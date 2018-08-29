"""
Main module for interfacing to hardware in and attached to the HUZZAH32

Written by Lucien Gaitskell (2018)
"""

from machine import UART, I2C, Pin, SPI, RTC
import utime
import os


from devices import adafruit_lis3dh, adafruit_sdcard, ssd1306, esp32_batv, adafruit_gps, sim800l

'''
from rowing.devices import adafruit_gps
#print("HW IMPORT 1: {} bytes".format(gc.mem_alloc()))
from rowing.devices import ssd1306
#print("HW IMPORT 2: {} bytes".format(gc.mem_alloc()))
from rowing.devices import adafruit_lis3dh
#print("HW IMPORT 3: {} bytes".format(gc.mem_alloc()))
from rowing.devices import sim800l
#print("HW IMPORT 4: {} bytes".format(gc.mem_alloc()))
from rowing.devices import adafruit_sdcard
#print("HW IMPORT 5: {} bytes".format(gc.mem_alloc()))
'''


class Hardware:
    """ Handles high level management of all hardware devices. """

    SD_PATH = '/sd'

    def __init__(self, sd=True):
        # ESP32 Battery:
        self.battery = esp32_batv.BatteryVoltage()

        # GPS // UART Setup:
        self.gps = adafruit_gps.GPS(
            UART(1, 9600, timeout=3000, tx=17, rx=16)
        )

        # Software I2C bus setup:
        self.i2c = I2C(-1, sda=Pin(23), scl=Pin(22), freq=800000)

        # OLED setup:
        self._oled_rst = Pin(15, mode=Pin.OUT)
        self._oled_rst.value(0)
        utime.sleep_ms(20)
        self._oled_rst.value(1)
        utime.sleep_ms(20)
        self.oled = ssd1306.SSD1306_I2C(128, 64, self.i2c)

        # Accelerometer setup:
        self.accel = adafruit_lis3dh.LIS3DH_I2C(self.i2c)
        self.accel.data_rate = adafruit_lis3dh.DATARATE_400_HZ

        # SD Card:
        if sd:
            self._sd_spi = SPI(1, sck=Pin(5, value=0), miso=Pin(19), mosi=Pin(18))
            self.sd = adafruit_sdcard.SDCard(self._sd_spi, Pin(33))
        else:
            self._sd_spi = None
            self.sd = None

        # Cell Modem:
        self.cellular_enable = Pin(4, mode=Pin.OUT)
        self.cellular = sim800l.SIM800L(2, rx=27, tx=33)
        self.cellular.wakechars()

        # Buttons:
        self.pin_power = Pin(13, pull=Pin.PULL_DOWN, mode=Pin.IN)

    def _wait_for_ready(self):
        gps_success = 5  # Number of successes to allow pass

        while True:  # Loop until ready
            self.gps.update()
            t = self.gps.timestamp_utc
            if t is not None:
                gps_success -= 1
                if gps_success <= 0:
                    RTC().datetime(
                        (t.tm_year, t.tm_mon, t.tm_mday, t.tm_wday,
                         (t.tm_hour + 20) % 24,  # Correct for timezone (UTC -> EST)
                         t.tm_min, t.tm_sec, None))
                    print("Time is now: {}".format(RTC().datetime()))
                    break

    def run_splash(self):
        # Clear #1
        self.oled.fill(0)
        self.oled.show()
        utime.sleep_ms(50)

        # Show splash
        self.oled.text("Row Meter", 25, 32)
        self.oled.text("Luc G", 30, 42)
        self.oled.show()
        #utime.sleep_ms(2000)

        ENSURE_SLEEP = 1000
        ts = utime.ticks_ms()
        self._wait_for_ready()
        t_elap = utime.ticks_diff(utime.ticks_ms(), ts)
        if t_elap < ENSURE_SLEEP:
            utime.sleep_ms(ENSURE_SLEEP-t_elap)

        # Clear #2
        self.oled.fill(0)
        self.oled.show()

    def setup(self):
        """
        Setup ALL hardware devices attached to HUZZAH32
        """

        '''
        ## SD
        ## GPS:
        - Mode: # TODO
        ## OLED
        ## CELLULAR
        '''
        if self.sd:
            os.mount(self.sd, self.SD_PATH)

        self.gps.send_command(adafruit_gps.NMEA_OUTPUT_RMCGGA)
        self.gps.send_command(adafruit_gps.NMEA_UPDATE_2HZ)
        self.gps.send_command(adafruit_gps.FIX_CTL_1HZ)

        self.oled.contrast(255)

        #self.cellular_enable.value(1)
        #utime.sleep_ms(50)
        #self.cellular.setup()
        #self.cellular.send_sms(b'14012975454', b'START')

    def close(self):
        if self._sd_spi:
            self._sd_spi.deinit()

    def sleep(self):
        self.gps.send_command(adafruit_gps.STANDBY)  # Enter sleep mode
        self.accel.data_rate = adafruit_lis3dh.DATARATE_POWERDOWN  # Disable accelerometer
        self.cellular_enable.value(0)
