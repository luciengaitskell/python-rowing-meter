from devices.adafruit_gps import GPS, GPSPoint, point_m_dist

import uasyncio as asyncio
import utime


POINT_TRACK_TIMEOUT = 20


class LocTracker:
    def __init__(self, gps: GPS, log, sd_lock, dist_enabler: callable = None):
        self.gps = gps
        #self.points = []

        self.running = False

        self.last_point_time = None
        self.last_point = None
        self.dist = 0
        self.l = log
        self.sd_lock = sd_lock
        if dist_enabler is not None:
            self.dist_en = dist_enabler
        else:
            self.dist_en = True

    def data_tick(self):
        new_d = False  # Prevent overlogging -- flags if new data read
        while self.gps.any_updates():  # Process through all available updates
            new_d = True
            try:
                self.gps.update()
            except ValueError as e:
                print("GPS Decode Error: {}".format(e))
                with self.sd_lock: self.l.log({'event': "READ_FAIL", 'desc': "DECODE_ERROR", 'error': str(e)})
                return
            except Exception as e:
                print("General GPS ERROR")
                with self.sd_lock: self.l.log({'event': "READ_FAIL", 'desc': "GENERAL_ERROR", 'error': str(e)})
                return

        if not new_d: return False  # Return if no new data

        # Every second print out current location details if there's a fix.
        current = utime.time()

        if not self.gps.has_fix:
            # Try again if we don't have a fix yet.
            with self.sd_lock: self.l.log({'state': "NO_FIX"})
            print('Waiting for fix...')
            return

        new_point = GPSPoint.from_current(self.gps)

        with self.sd_lock:
            self.l.log({'lat': new_point.lat, 'lon': new_point.lon, 'spd': new_point.spd})

        # Track/Update distance count every half second:
        if self.last_point_time is None or current - self.last_point_time >= 0.5:
            self.last_point_time = current

            if self.last_point is not None:
                # Add new point movement distance to total (if enabled)
                if self.dist_en is True or (callable(self.dist_en) and self.dist_en()):
                    self.dist += point_m_dist(new_point, self.last_point)

                #if current-self.last_point.ts >= POINT_TRACK_TIMEOUT:
                #    self.points.append(new_point)
            self.last_point = new_point
        return True

    async def run_async(self, delay=500):
        while True:
            self.data_tick()
            await asyncio.sleep(delay/1000.)

    def thread(self, delay=500):
        self.running = True
        while self.running:
            self.data_tick()
            utime.sleep_ms(delay)
