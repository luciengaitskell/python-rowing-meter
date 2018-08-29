# General:
from micropython import const


# UI
from rowing.display import DisplayHandler
from rowing.display.elements.text import TextBox
from rowing.display.elements.bar import Bar
from rowing.display.font.packaged import arial10, arial12, arial20, arial25, arial15


_WIDTH = const(128)
_HEIGHT = const(64)

# Y:
_HEADER = const(10)
_FOOTER = const(_HEIGHT - 22)

# X:
_Q1 = int(_WIDTH / 4) - 1
_T1 = int(_WIDTH / 3) - 1
_CENTER = int(_WIDTH / 2) - 1
_Q3 = int(3 * _WIDTH / 4) - 1

class RowUI:
    def __init__(self, dh: DisplayHandler, setup=True):
        self._d = dh

        if setup: self._setup()

    def _setup(self):
        # Header:
        self.time = self._d.add(TextBox(0, 0, arial10))
        self.batv = self._d.add(TextBox(42, 0, arial10))
        self.gps = self._d.add(TextBox(108, 0, arial10))
        ## Y Divider:
        self._d.draw_fill_box((0, _HEADER), (_WIDTH - 1, _HEADER), col=1)

        # Main Body:
        body_large_y = 16
        self.stroke = self._d.add(TextBox(9, body_large_y, arial25))
        self.speed = self._d.add(TextBox(_CENTER + 10, body_large_y, arial25))
        #self.cell_signal = self._d.add(Bar(Bar.VERT_B, (_T1+1, _HEADER+1), (_CENTER-1, _FOOTER-1)))
        ## X Divider:
        x = _T1; self._d.draw_fill_box((x, _HEADER + 1), (x, _FOOTER), col=1)
        x = _CENTER; self._d.draw_fill_box((x, _HEADER + 1), (x, _HEIGHT - 1), col=1)

        # Footer:
        footer_y = _FOOTER + 4
        self.chrono = self._d.add(TextBox(2, footer_y + 2, arial12))
        self.distance = self._d.add(TextBox(_CENTER + 8, footer_y, arial20))
        ## Y Divider:
        self._d.draw_fill_box((0, _FOOTER), (_WIDTH - 1, _FOOTER), col=1)

    def update(self):
        self._d.update()
