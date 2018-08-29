# The MIT License (MIT)
#
# Copyright (c) 2016 Scott Shawcroft for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Taken from Adafruit, and modified by Lucien Gaitskell (2018)

* Converted for MicroPython and it's supporting libraries
"""

from machine import Pin, SPI

class SPIDevice:
    """
    Represents a single SPI device and manages locking the bus and the device
    address.

    :param SPI spi: The SPI bus the device is on
    :param ~microcontroller.Pin chip_select: The chip select pin

    Example::

        from machine import SPI
        from rowing.devices.support.spi_device import SPIDevice

        spi = SPI(0)
        device = SPIDevice(spi, Pin(18))

        with device:
            device.spi.read(4)
        # A second transaction
        with device:
            device.write(bytes([0,0,0,0]))
    """
    def __init__(self, spi: SPI, cs: Pin, baudrate=100000, polarity=0, phase=0, *,
                 sck=None, mosi=None, miso=None):
        # General SPI config:
        self.spi = spi
        self.baudrate = baudrate
        self.polarity = polarity
        self.phase = phase

        # SPI Pin deviations:
        self.sck = sck
        self.mosi = mosi
        self.miso = miso

        # Chip select setup
        self.chip_select = cs
        cs.init(value=0, mode=Pin.OUT)

    def __enter__(self):
        self.spi.init(baudrate=self.baudrate, polarity=self.polarity, phase=self.phase,
                      sck=self.sck, mosi=self.mosi, miso=self.miso)

        self.chip_select.value(False)
        return self.spi

    def __exit__(self, *exc):
        self.chip_select.value(True)
        self.spi.deinit()  # TODO: necessary?
        return False
