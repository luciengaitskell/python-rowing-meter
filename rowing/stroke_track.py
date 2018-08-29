from micropython import const
import uasyncio as asyncio
import utime

from devices.adafruit_lis3dh import LIS3DH_I2C
from rowing.util.logging import TransLog


STROKE_WINDOW = const(10000)  # ms
STROKE_DELAY = const(200)
STROKE_THRESH = 2.0  # m/s^2
GRAV_CONST = 9.81  # m/s^2

class StrokeTracker:
    def __init__(self, accel: LIS3DH_I2C, log: TransLog, i2c_lock, sd_lock):
        self._acc = accel  # Accelerometer
        self._log = log  # Log

        self.running = False

        self.i2c_lock = i2c_lock
        self.sd_lock = sd_lock
        self.last_acc_mag = None  # Last accelerometer magnitude

        self._strokes = []  # Last strokes (stored as list of times (ms))
        self._in_stroke = False  # Is currently in stroke?
        self._last_in_stroke = None  # Last updated time in stroke

    def data_tick(self):
        try:
            with self.i2c_lock:
                acc = self._acc.acceleration
            a_mag = abs((acc.x**2 + acc.y**2 + acc.z**2) ** (1/2) - GRAV_CONST)  # Read accelerometer magnitude
        except:
            with self.sd_lock: self._log.log({'state': "ERROR", 'desc': "Failed to read"})
            a_mag = 0
        else:
            with self.sd_lock:
                self._log.log({'x': acc.x, 'y': acc.y, 'z': acc.z, 'mag': a_mag, 'spm': self.stroke_rate})

        # Add stroke if newly broke threshold:
        if a_mag > STROKE_THRESH:
            if not self._in_stroke:

                # Calculate time since last stroke was detected:
                stroke_diff = utime.ticks_diff(utime.ticks_ms(), self._last_in_stroke)

                if stroke_diff > STROKE_DELAY:  # Count as new stroke only if outside delay
                    self._log.log({'alert': "STROKE"})
                    print("=======STROKE=======")
                    self._strokes.append(utime.ticks_ms())

            self._in_stroke = True  # Set currently in stroke
            self._last_in_stroke = utime.ticks_ms()  # Update last time in stroke
        else:
            self._in_stroke = False  # Set not currently in stroke

        # Remove old points:
        for idx in reversed(range(len(self._strokes))):
            s = self._strokes[idx]
            if utime.ticks_diff(utime.ticks_ms(), s) > STROKE_WINDOW:
                del self._strokes[idx]

    @property
    def stroke_rate(self):
        """
        :return: Measured stroke rate, in strokes per minute (int).
        """
        n_strokes = len(self._strokes)
        if n_strokes < 2: return 0

        window = utime.ticks_diff(self._strokes[-1], self._strokes[0])
        #window = STROKE_WINDOW
        sr = int((60000./window) * n_strokes)
        if sr >= 100: sr = 99
        return sr

    def in_motion(self):
        """
        :return: If stroke rate is above 0
        """
        return self.stroke_rate > 0

    #async def auto(self, delay=10):
    def thread(self, delay=10):
        self.running = True
        while self.running:
            s = utime.ticks_ms()
            self.data_tick()

            elapsed_ms = utime.ticks_diff(utime.ticks_ms(), s)
            sleep_s = delay/1000. - elapsed_ms / 1000.
            if sleep_s < 0:
                print("Accelerometer delay stretching! ({}s)".format(-sleep_s))
                sleep_s = 0

            #await asyncio.sleep(sleep_s)
            utime.sleep(sleep_s)
