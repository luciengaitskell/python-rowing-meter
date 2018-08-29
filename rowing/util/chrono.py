import utime


def _curr_tick():
    return utime.ticks_ms()


class Chrono:
    def __init__(self, enabler: callable):
        self.e = enabler

        self._t = 0
        self._t_last = None
        self._t_elapsed = None

    @property
    def time(self):
        self.tick()
        return self._t

    def tick(self):
        en = self.e()

        curr = _curr_tick()
        if self._t_last is not None:
            self._t = self._t + utime.ticks_diff(curr, self._t_last)

        if en:
            self._t_last = curr
        else:
            self._t_last = None
