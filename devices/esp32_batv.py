"""
Easy implementation for ESP32 Battery voltage monitor

Written by Lucien Gaitskell, 2018
"""
from machine import ADC, Pin


_SCALE = (3.5 / 4095) * 2  # adc scale * voltage divider


class BatteryVoltage:
    def __init__(self):
        # Setup ADC:
        self.batv = ADC(Pin(35))  # Analog A13 -- battery monitor

        # Set attenuation and bit width:
        self.batv.atten(ADC.ATTN_11DB)
        self.batv.width(ADC.WIDTH_12BIT)

    def read(self):
        return self.batv.read()

    def get_volt(self, val):
        return val * _SCALE

    def read_volt(self):
        return self.get_volt(self.read())
