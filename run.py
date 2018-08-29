import utime
import _thread
import uasyncio as asyncio
import machine as m


from rowing.ui import RowUI
from rowing.display import DisplayHandler
from rowing.hardware import Hardware

# Movement tracking:
from rowing.loc_track import LocTracker
from rowing.stroke_track import StrokeTracker

# Logging:
from rowing.util.logging import Log, TransLog

# Chrono:
from rowing.util.chrono import Chrono


RTC = m.RTC()

VOLT_PERC = [(4.2, 100),
             (4.1, 90),
             (4.0, 80),
             (3.9, 60),
             (3.8, 40),
             (3.7, 20),
             (3.6, 10),
             (3.5, 5),
             (3.0, 0)]

_running = True
# Async:
_main_loop = asyncio.get_event_loop()
_acc_loop = asyncio.EventLoop(16, 16)

# Log:
_event_log = Log('/sd/event_log.txt')
_trans_log = Log('/sd/trans_log.txt')
# TODO: ADD RTC FOR LOGGING

# Components:
# #MAIN Hardware:
_hw = Hardware()

# Interface Locks:
i2c_lock = _thread.allocate_lock()
sd_lock = _thread.allocate_lock()

# #Middleware:
_dh = DisplayHandler(_hw.oled, i2c_lock=i2c_lock)
_ui = RowUI(_dh, setup=False)
_st = StrokeTracker(_hw.accel, TransLog('accel', log=_trans_log, log_tout=None), i2c_lock, sd_lock)
_pt = LocTracker(_hw.gps, TransLog('gps', log=_trans_log), sd_lock, dist_enabler=_st.in_motion)

# Timer:
_chrono = Chrono(_st.in_motion)


# ESSENTIAL STATE FUNCTIONS:
def _setup():
    _hw.setup()
    _hw.run_splash()  # Hangs for duration
    _ui._setup()
    _event_log.open()
    _trans_log.open()
    _event_log.log({'state': "START"})
    _trans_log.log({'alert': "NEW_SESSION"})


def _run():
    #_thread.start_new_thread(_pt.thread, (200,))
    _thread.start_new_thread(_st.thread, (100,))

    #_thread.start_new_thread(_acc_loop.run_forever, ())

    # HANG until interrupt:
    _main_loop.run_forever()


def _close():
    global _running
    _running = False
    _st.running = False
    _pt.running = False

    _main_loop.stop()  # Ensure stopped
    _acc_loop.close()  # Forcefully close

    utime.sleep_ms(300)

    _event_log.ensure_close()
    _trans_log.ensure_close()
    _hw.close()


def _exec_sleep():
    global _running
    ## Tell modules to sleep:
    _running = False

    # Reg wake:
    _hw.pin_power.irq(trigger=m.Pin.WAKE_HIGH, wake=m.DEEPSLEEP)
    print("Trigger wake on {}".format(_hw.pin_power))

    # SLEEP ESP32 (until trigger):
    print("FAREWELL!")
    _event_log.log({'state': "SLEEPING"})
    utime.sleep_ms(10)

    # EMPTY DISPLAY
    _dh.draw_fill(0)
    _dh.update(False)

    _hw.sleep()
    _close()

    utime.sleep_ms(50)

    m.deepsleep()


# --- ASYNC UPDATES --- #:
async def _sleep_handler():
    prev_p = 0
    p_start = None

    while _running:
        #if _hw.pin_power.value() == 1:
        #    while _hw.pin_power.value() == 1:
        #        await asyncio.sleep(0.1)
        #    print("==EXECUTING SLEEP==")
        #    _exec_sleep()

        curr_p = _hw.pin_power.value()
        if curr_p == 1 and prev_p == 0:
            p_start = utime.ticks_ms()

        if curr_p == 0 and prev_p == 1:
            if utime.ticks_diff(utime.ticks_ms(), p_start) > 2000:
                print("==EXECUTING SLEEP==")
                _exec_sleep()
        prev_p = curr_p
        await asyncio.sleep(0.1)


_DISPLAY_HZ = 5


async def _ui_update():
    while _running:
        s = utime.ticks_ms()
        # Battery:
        bv = _hw.battery.read_volt()
        bp = None
        for volt in VOLT_PERC:
            if bv >= volt[0]:
                bp = volt[1]
                break
        _ui.batv.text = "{:02}%".format(bp)
        #_ui.batv.text = "{:04.2f}".format(_hw.battery.read_volt())

        # Time
        t = RTC.datetime()
        _ui.time.text = "{:02}:{:02}".format(t[4], t[5])

        # GPS
        # # Speed, Fix Indicator:
        _ui.speed.text = " -.-- "  # Assume no speed
        if _hw.gps.has_fix:
            _ui.gps.text = "GPS"

            sp = _hw.gps.speed_knots
            if sp is not None:
                # Convert to m/s:
                sp *= 0.5144  # <- m/s = 1 kt
                _ui.speed.text = "{:.2f}".format(float(sp))
        else:
            _ui.gps.text = "XFX"

        # #  Distance:
        _ui.distance.text = "{:05}".format(int(_pt.dist))

        # Accelerometer:
        _ui.stroke.text = "{:2d}".format(_st.stroke_rate)

        ct_ms = _chrono.time
        ct_hrs = int(ct_ms / (3600*1000))
        ct_ms -= int((3600*1000) * ct_hrs)
        ct_mins = int(ct_ms / (60*1000))
        ct_ms -= (60*1000) * ct_mins
        ct_sec = int(ct_ms/1000)
        ct_ms -= ct_sec * 1000
        _ui.chrono.text = "{:01}:{:02}:{:02}.{:01}".format(ct_hrs, ct_mins, ct_sec, round(ct_ms/100))

        #_ui.cell_signal.level = random.random()
        _ui.update()

        elapsed_ms = utime.ticks_diff(utime.ticks_ms(), s)
        sleep_s = 1. / _DISPLAY_HZ - elapsed_ms / 1000.
        if sleep_s > 0:
            #print("sleep: ", sleep_s)
            pass
        else:
            print("Display delay stretching! ({}s)".format(-sleep_s))
            sleep_s = 0.001
        await asyncio.sleep(sleep_s)


# Async task creation:
def _create_pri_tasks(l):
    async def _cell_status():
        while _running:
            print("Cell signal: {}".format(_hw.cellular.signal_strength()))
            await asyncio.sleep(10)
    async def _battery_log():
        while _running:
            with sd_lock: _trans_log.log({'volt': _hw.battery.read_volt()})
            await asyncio.sleep(60)

    l.create_task(_pt.run_async(250))
    l.create_task(_ui_update())
    #l.create_task(_cell_status())
    l.create_task(_sleep_handler())
    l.create_task(_battery_log())


def _create_sec_tasks(l):
    #l.create_task(_st.auto(75))
    pass

def main():
    try:
        # General setup:
        _setup()

        # Setup async functions:
        _create_pri_tasks(_main_loop)
        _create_sec_tasks(_acc_loop)

        # ===RUN===:
        _run()
    finally:
        _close()
