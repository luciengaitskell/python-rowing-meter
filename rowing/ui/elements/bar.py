from . import Element

class Bar(Element):
    VERT_T = 1
    VERT_B = 3
    HORZ_L = 2
    HORZ_R = 4

    def __init__(self, dir, b1, b2):
        super().__init__()
        if dir not in (self.VERT_T, self.VERT_B, self.HORZ_L, self.HORZ_R):
            raise ValueError("Not valid direction.")
        self._d = dir
        self.bx1 = b1[0]
        self.by1 = b1[1]
        self.bx2 = b2[0]
        self.by2 = b2[1]

        self._l = 0

    @property
    def level(self):
        return self._l

    @level.setter
    def level(self, l):
        if not 0 <= l <= 1:
            raise ValueError("Level needs to be [0,1]")
        self._l = l

    def _draw(self):
        """ Draw element """
        horz = (self._d % 2 == 0)

        if horz:
            max = self.bx2 - self.bx1
        else:
            max = self.by2 - self.by1

        fill = round(self._l*max)

        '''
        if horz:
            if self._d == self.HORZ_R:
                x = self.bx2-fill
            elif self._d == self.HORZ_L:
                x = self.bx1 + fill'''

        if not self._d == self.VERT_B: raise ValueError("Direction not supported.")
        self.display.draw_fill_box((self.bx1, self.by1), (self.bx2, self.by2-fill), col=0)
        self.display.draw_fill_box((self.bx1, self.by2 - fill), (self.bx2, self.by2), col=1)
