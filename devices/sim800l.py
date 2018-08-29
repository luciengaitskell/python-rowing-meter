# Driver for SIM800L module (using AT commands)
# MIT License; Copyright (c) 2017 Jeffrey N. Magee


from machine import UART
import math
import utime

REPLY_OK = True
REPLY_ERROR = False
REPLY_TIMEOUT = None

HTTP_GET = 0
HTTP_POST = 1
HTTP_HEAD = 2


# kludge required because "ignore" parameter to decode not implemented
def _convert_to_string(buf):
    try:
        tt = buf.decode('utf-8').strip()
        return tt
    except UnicodeError:
        tmp = bytearray(buf)
        for i in range(len(tmp)):
            if tmp[i]>127:
                tmp[i] = ord('#')
        return bytes(tmp).decode('utf-8').strip()


class SIM800LError(Exception):
    pass


def _check_result(errmsg, expected, res):
    if not res:
        res = 'None'
    #print(errmsg+res)
    if not expected == res and not res == 'None':
        raise SIM800LError('SIM800L Error {}  {}'.format(errmsg,res))


class SIM800L:
    def __init__(self, id: int, **kwargs):
        self._uart = UART(id, 9600, **kwargs)
        self.incoming_action = None
        self.no_carrier_action = None
        self.clip_action = None
        self._clip = None
        self.msg_action = None
        self._msgid = 0
        self.credit = ''
        self.credit_action = None

    def callback_incoming(self,action):
        self.incoming_action = action

    def callback_no_carrier(self,action):
        self.no_carrier_action = action

    def callback_clip(self,action):
        self.clip_action = action

    def callback_credit_action(self,action):
        self.credit_action = action

    def get_clip(self):
        return self._clip

    def callback_msg(self,action):
        self.msg_action = action

    def get_msgid(self):
        return self._msgid

    def process_resp(self, detect_str=None, waitfor=1000):
        t_last = utime.ticks_ms()

        state = REPLY_TIMEOUT
        result = b''
        while utime.ticks_diff(utime.ticks_ms(), t_last) < waitfor:
            if self._uart.any():
                buf = self._uart.readline()

                if buf == b'\r\n': continue  # Discard 'empty' lines

                buf = buf.strip()  # Strip newlines/carriage returns

                # Signals end of response:
                if b'OK' in buf:
                    state = REPLY_OK
                    break
                if b'ERROR' in buf:
                    state = REPLY_ERROR
                    break

                result += buf + b'\n'

                if detect_str is not None and detect_str in buf:
                    break

        return state, result.strip()

    def command(self, cmd: bytes, lines=1, waitfor=1000, detect_str=None, end=None, msgtext: bytes=None):
        #flush input
        #print(cmdstr)
        while self._uart.any():
            self._uart.read(1)

        if end is None: end = b'\n'
        self._uart.write(cmd + end)
        if msgtext:
            t_last = utime.ticks_ms()
            while utime.ticks_diff(utime.ticks_ms(), t_last) < 1000:
                if self._uart.any():
                    buf = self._uart.readline()
                    if b'>' in buf: break
            self._uart.write(msgtext + b'\x1A')
        return self.process_resp(detect_str=detect_str, waitfor=waitfor)


    def setup(self):
        self.command(b'ATE0')         # command echo off
        #self.command(b'AT+CRSL=99\n')   # ringer level
        #self.command(b'AT+CMIC=0,10\n') # microphone gain
        #self.command(b'AT+CLIP=1\n')    # caller line identification
        self.command(b'AT+CMGF=1')    # plain text SMS
        #self.command(b'AT+CALS=3,0\n')  # set ringtone
        #self.command(b'AT+CLTS=1\n')    # enable get local timestamp mode
        self.command(b'AT+CSCLK=0')   # disable automatic sleep

    def wakechars(self):
        self._uart.write(b'AT')        # will be ignored

    def sleep(self,n):
        self.command(b'AT+CSCLK=T%d' % n)

    def sms_alert(self):
        self.command(b'AT+CALS=1,1')  # set ringtone
        utime.sleep_ms(3000)
        self.command(b'AT+CALS=3,0')  # set ringtone

    def call(self,numstr):
        self.command(b'ATD%s;' % numstr)

    def hangup(self):
        self.command(b'ATH')

    def answer(self):
        self.command(b'ATA')

    def set_volume(self,vol):
        if 0 <= vol <= 100:
            self.command(b'AT+CLVL=%d' % vol)

    def signal_strength(self):
        s, result = self.command(b'AT+CSQ')
        if s:
            params = result.split(b',')
            if not params[0] == b'':
                params2 = params[0].split(b':')
                if b'+CSQ' in params2[0]:
                    x = int(params2[1])
                    if not x == 99:
                        return math.floor(x/6+0.5)
        return 0

    def battery_charge(self):
        s, result = self.command(b'AT+CBC')
        if s:
            params=result.split(b',')
            if not params[0] == '':
                params2 = params[0].split(b':')
                if b'+CBC' in params2[0]:
                    return int(params[1])
        return 0

    def network_name(self):
        s, result = self.command(b'AT+COPS?')
        if s:
            params=result.split(b',')
            if not params[0] == '':
                params2 = params[0].split(b':')
                if params2[0] == b'+COPS':
                    if len(params) > 2:
                        names = params[2].split(b'"')
                        if len(names) > 1:
                            return names[1]
        return b''

    def read_sms(self, id):
        s, result = self.command(b'AT+CMGR=%d' % id)
        if s:
            params=result.split(b',')
            if not params[0] == b'':
                params2 = params[0].split(b':')
                if b'+CMGR' in params2[0]:
                    number = params[1].replace(b'"', b' ').strip()
                    date = params[3].replace(b'"', b' ').strip()
                    time = params[4].replace(b'"', b' ').strip()
                    return number, date, time, result
        return None

    def send_sms(self, destno, msgtext):
        s, result = self.command(b'AT+CMGS="%s"' % destno, msgtext=msgtext)
        if s:
            params = result.split(b':')
            if b'+CUSD' in params[0] or b'+CMGS' in params[0]:
                return True
        return False

    def check_credit(self):
        self.command(b'AT+CUSD=1,"*100#"')

    def get_credit(self):
        return self.credit

    def delete_sms(self,id):
        self.command(b'AT+CMGD=%d' % id)

    def date_time(self):
        s, result = self.command(b'AT+CCLK?')
        if s:
            if result[0:5] == b"+CCLK":
                return result.split(b'"')[1]
        return b''

    def check_incoming(self):
        if self._uart.any():
            buf=self._uart.readline()
            # print(buf)
            buf = _convert_to_string(buf)
            params=buf.split(',')
            if params[0] == "RING":
                if self.incoming_action:
                    self.incoming_action()
            elif params[0][0:5] == "+CLIP":
                params2 = params[0].split('"')
                self._clip = params2[1]
                if self.clip_action:
                    self.clip_action()
            elif params[0][0:5] == "+CMTI":
                self._msgid = int(params[1])
                if self.msg_action:
                    self.msg_action()
            elif params[0][0:5] == "+CUSD":
                if len(params)>1:
                    st = params[1].find('#')
                    en = params[1].find('.',st)
                    en = params[1].find('.',en+1)
                    if st>0 and en>0:
                        self.credit = '£'+params[1][st+1:en]
                        if self.credit_action:
                            self.credit_action()
            elif params[0] == "NO CARRIER":
                    self.no_carrier_action()

    def gprs_setup(self, apn=b"wholesale"):
        setup = self.command(b'AT+SAPBR=3,1,"Contype","GPRS"', waitfor=1000)[0]
        setup &= self.command(b'AT+SAPBR=3,1,"APN","%s"' % apn, waitfor=1000)[0]

        if not setup: raise OSError("Failed to setup GPRS")
        self.command(b'AT+SAPBR=1,1')
        return True

    def http_setup(self):
        # now do http request
        setup = self.command(b'AT+HTTPINIT')[0]
        if not setup: print("Failed to init HTTP service")
        config = self.command(b'AT+HTTPPARA="CID",1')[0]
        if not config: print("Failed to configure HTTP service")
        return True

    def http(self, url, action=HTTP_GET):
        resp = None

        # Split URL:
        proto, dummy, surl = url.split("/", 2)

        if proto == "http:":
            is_ssl = 0
        elif proto == "https:":
            is_ssl = 1
        else:
            raise ValueError("Unsupported protocol: " + proto)

        try:
            s = self.command(b'AT+HTTPPARA="URL","%s"' % surl)[0]
            s &= self.command(b'AT+HTTPSSL=%d' % is_ssl)[0]
            s &= self.command(b'AT+HTTPACTION=%d' % action)[0]
            ts = utime.ticks_ms()
            nbytes = None

            while utime.ticks_diff(utime.ticks_ms(), ts) < 20000:
                if self._uart.any():
                    buf = self._uart.readline()
                    if buf and not buf == b'\r\n' and not buf == b'':
                        buf = _convert_to_string(buf)
                        print(buf)
                        prefix,retcode,bts = buf.split(',')
                        rstate = int(retcode)
                        nbytes = int(bts)
                        break
            if nbytes is None: raise OSError("HTTP ACTION NOT COMPLETE")
            res = self.command(b'AT+HTTPREAD')[1]
            buf = self.command(b'')[1]
            #buf = self._uart.read(nbytes)
            #_check_result("HTTPACTION: ", '+HTTPREAD: {}'.format(nbytes), res)
            #if buf[-4:] == 'OK\r\n':  # remove final OK if it was read
            #    buf = buf[:-4]
            resp = Response(buf)
        except SIM800LError as err:
            print(str(err))
        return resp

    def http_close(self):
        self.command(b'AT+HTTPTERM')  # terminate HTTP task

    def gprs_close(self):
        self.command(b'AT+SAPBR=0,1')  # close Bearer context



class Response:
    def __init__(self, buf, status=200):
        self.encoding = "utf-8"
        self._cached = buf
        self.status = status
    
    def close(self):
        self._cached = None
    
    @property
    def content(self):
        return self._cached
    
    @property
    def text(self):
        return str(self.content, self.encoding)

    # noinspection PyUnresolvedReferences
    def json(self):
        import ujson
        return ujson.loads(self.content)
