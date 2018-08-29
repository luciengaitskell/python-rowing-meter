from devices.ssd1306 import SSD1306

from rowing.display.elements import Element


class DisplayHandler:
    def __init__(self, d: SSD1306, i2c_lock=None):
        self.d = d
        self.els = []  # List of `Element`s
        self.i2c_lock = i2c_lock

    def add(self, e: Element) -> Element:
        if e in self.els: raise ValueError("Element already member.")

        self.els.append(e)
        e.draw(self)
        return e

    @property
    def framebuf(self):
        return self.d.framebuf

    # Essential interface:
    def draw_fill(self, col):
        self.d.fill(col)

    def draw_pixel(self, x, y, col):
        self.d.pixel(x, y, col)

    def draw_text(self, string, x, y, col=1):
        self.d.text(string, x, y, col)

    def draw_scroll(self, dx, dy):
        self.d.scroll(dx, dy)

    # Extension:
    def draw_fill_box(self, ul, lr, col):
        for x in range(ul[0], lr[0]+1):
            for y in range(ul[1], lr[1]+1):
                self.draw_pixel(x, y, col)

    def update(self, update_els=True):
        """ Show updates on screen. """
        if update_els:
            for e in self.els:
                e.draw(self)

        if self.i2c_lock is not None:  # Use coms lock if given
            with self.i2c_lock:
                self.d.show()
        else:
            self.d.show()
