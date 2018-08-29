class Element:
    def __init__(self):
        self.display = None  # DisplayHandler
        self._en = True

    # En-/disable:
    def enable(self): self._en = True

    def disable(self): self._en = False

    # Update:
    def draw(self, display):  # DisplayHandler
        if self._en:
            self.display = display
            try:
                self._draw()
            finally:
                self.display = None

    # For subclasses
    def _draw(self):
        raise NotImplementedError
