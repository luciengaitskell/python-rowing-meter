"""
Main module for interfacing to hardware in and attached to the HUZZAH32

Written by Lucien Gaitskell (2018)
"""

from machine import UART, I2C, Pin
from devices import adafruit_gps, ssd1306


class Hardware:
    """ Handles high level management of all hardware devices. """

    def __init__(self):
        #self.uart2 = UART(2, 9600, tx=17, rx=16)

        # GPS // UART Setup:
        self.gps = adafruit_gps.GPS(
            UART(1, 9600, timeout=3000, tx=17, rx=16)
        )

        # Software I2C bus setup:
        self.i2c = I2C(-1, sda=Pin(23), scl=Pin(22), freq=100000)

        # OLED setup:
        self.oled = ssd1306.SSD1306_I2C(128, 64, self.i2c)

    def setup(self):
        """
        Setup ALL hardware devices attached to HUZZAH32
        """

        '''
        ## GPS:
        - Mode: # TODO
        '''
        self.gps.send_command('PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
        self.gps.send_command('PMTK220,1000')
