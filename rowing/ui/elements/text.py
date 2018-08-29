# A text box handling elemetn
# Lucien Gaitskell June 2018
# Modified from: writer.py Implements the Writer class (V0.2 Peter Hinch Dec 2016)

# The MIT License (MIT)
#
# Copyright (c) 2016 Peter Hinch
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

# A Writer supports rendering text to a Display instance in a given font.
# Multiple Writer instances may be created, each rendering a font to the
# same Display object.

import framebuf

from . import Element


class TextBox(Element):
    def __init__(self, x_ul, y_ul, font):
        super().__init__()
        self.font = font
        # Allow to work with any font mapping
        if font.hmap():
            self.map = framebuf.MONO_HMSB if font.reverse() else framebuf.MONO_HLSB
        else:
            raise ValueError('Font must be horizontally mapped.')

        # Area color / text color:
        self.a_col = 0
        self.t_col = 1

        # Upper left corner:
        self._ul = (x_ul, y_ul)

        # Set text:
        self._text = ""
        # Last drawn dimensions:
        self._last_dim = (0,0)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        if not isinstance(value, str):
            value = str(value)
        self._text = value

    def _draw(self):
        width = 0  # Text width
        height = 0  # Text height (Max char height)

        for char in self._text:
            cw, ch = self._printchar(char, dx=width)
            width += cw  # Add width to total
            if ch > height: height = ch  # Set height if larger than last

        if self._last_dim[0] > width:
            self.display.draw_fill_box((self._ul[0]+width, self._ul[1]),
                                       (self._ul[0] + self._last_dim[0] - 1, self._ul[1] + self._last_dim[1] - 1),
                                       col=0)
        self._last_dim = (width, height)

    # Method using blitting. Efficient rendering for monochrome displays.
    # Tested on SSD1306. Invert is for black-on-white rendering.
    def _printchar(self, char, invert=False, dx=0):
        glyph, char_height, char_width = self.font.get_ch(char)

        buf = bytearray(glyph)
        if invert:
            for i, v in enumerate(buf):
                buf[i] = 0xFF & ~ v
        fbc = framebuf.FrameBuffer(buf, char_width, char_height, self.map)

        self.display.framebuf.blit(fbc, self._ul[0]+dx, self._ul[1])
        return char_width, char_height

    def _printchar_bitwise(self, char, dx=0):
        glyph, char_height, char_width = self.font.get_ch(char)

        div, mod = divmod(char_height, 8)
        gbytes = div + 1 if mod else div  # No. of bytes per column of glyph

        for scol in range(char_width):  # Source column
            dcol = scol + self._ul[0] + dx  # Destination column
            drow = self._ul[1]  # Destination row
            for srow in range(char_height):  # Source row
                gbyte, gbit = divmod(srow, 8)

                if gbit == 0:  # Next glyph byte
                    data = glyph[scol * gbytes + gbyte]
                self.display.pixel(dcol, drow, data & (1 << gbit))
                drow += 1
        return char_width, char_height

    """
    def _printchar_bitwise(self, char, dx=0):
        glyph, char_height, char_width = self.font.get_ch(char)

        div, mod = divmod(char_height, 8)
        gbytes = div + 1 if mod else div  # No. of bytes per column of glyph
        for scol in range(char_width):  # Source column
            dcol = scol + self._ul[0] + dx  # Destination column
            drow = self._ul[1]  # Destination row
            for srow in range(char_height):  # Source row
                gbyte, gbit = divmod(srow, 8)
                if gbit == 0:  # Next glyph byte
                    data = glyph[scol * gbytes + gbyte]

                self.display.draw_pixel(dcol, drow, data & (1 << gbit))
                drow += 1
        return char_width, char_height"""
