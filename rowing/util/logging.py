import machine as m
import utime
import json

RTC = m.RTC()


def _t_epoch():
    """ Get current time in microseconds since Jan 1, 2000. """
    t = RTC.datetime()
    sec = utime.mktime(t[0:3] + t[4:7] + (t[3],) + (None,))
    return sec * (10 ** 6) + t[7]


class Log:
    """ Simplified implementation of logging into a file. """

    def __init__(self, path: str=None, *, log=None):
        if path is None and log is None:
            raise ValueError("Must supply either log path, or existing log")
        self.fp = path
        self._ext_log = log
        self._loc_fbuf = None

    @property
    def fbuf(self):
        if self._ext_log:  # Return external log file buffer (if supplied)
            return self._ext_log._loc_fbuf
        return self._loc_fbuf

    def open(self):
        if self._ext_log is None:  # Open given file path, if no external log
            self._loc_fbuf = open(self.fp, 'a')
        return self.fbuf

    def close(self):
        if self._ext_log is None:  # If no external log, close current file buffer
            self._loc_fbuf.close()
            self._loc_fbuf = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def ensure_close(self):
        if self._loc_fbuf is not None:  # If local file buffer is open, close it
            self.close()

    def log(self, d, inject_time=True):
        if self.fbuf is None: raise ValueError("File not opened")
        if isinstance(d, dict) and inject_time:
            d['ts'] = _t_epoch()
            d = json.dumps(d)
        elif not isinstance(d, str): d = str(d)

        while True:
            try:
                self.fbuf.write(d + "\n")
            except OSError:
                print("Write error... retry")
            else:
                break


class TransLog(Log):
    """ Easy logging for transducers. """

    def __init__(self, atype, *, path: str=None, log: Log=None, log_tout=None, **supporting_tags):
        """
        Create logger.

        :param path: Log data file path
        :param atype: Sensor overall type tag
        :param log_tout: Transducer log timeout/frequency; prevents logging at interval shorter than given rate (ms)
        :param supporting_tags: Extra tags/key words attached to logs
        """
        super().__init__(path=path, log=log)

        supporting_tags['atype'] = atype
        self.sup_kw = supporting_tags
        self._last_log_t = None  # Last log time
        self._tout = log_tout  # TODO: Implement log rate limiting (if supplied)

    @classmethod
    def from_log(cls, log: Log, *args, **kwargs):
        return cls(log.fp, *args, **kwargs)

    def should_log(self):
        """
        If log should occur, based on:
        has timeout, has been previous log, and was more recent than timeout
        """
        return not (self._tout is not None and
                    self._last_log_t is not None and
                    utime.ticks_diff(utime.ticks_ms(), self._last_log_t) < self._tout)

    def log(self, d, **supporting_tags):
        """
        Log line to file.

        :param d: Can be Any or specficially `dict`. `dict` prefered, as it wont be casted (more consistent).
        :param supporting_tags: Extra `dict` key/value pairs to be written.
        :return: None
        """
        if not self.should_log(): return  # Don't log if conditions aren't met

        self._last_log_t = utime.ticks_ms()
        msg = None
        if isinstance(d, dict):
            msg = dict(d)  # Copy data (to prevent accidental overwrite)
        else:
            msg = {'val': d}

        msg.update(supporting_tags)  # Add inputted supporting tags
        msg.update(self.sup_kw)  # Add global supporting tags
        super().log(msg, inject_time=True)

