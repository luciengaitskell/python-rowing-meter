# Driver for SIM800L module (using AT commands)
# MIT License; Copyright (c) 2017 Jeffrey N. Magee


from machine import UART
import math
import utime


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
        self.savbuf = None
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
    
    def command(self, cmd: bytes, lines=1, waitfor=500, msgtext: bytes=None):
        #flush input
        #print(cmdstr)
        st = utime.ticks_ms()
        while self._uart.any():
            self._uart.read(1)
        self._uart.write(cmd)
        if msgtext:
            self._uart.write(msgtext)
        delay = waitfor - utime.ticks_diff(utime.ticks_ms(), st)
        if delay > 0:
            utime.sleep_ms(delay)
        buf=self._uart.readline() #discard linefeed etc
        print(buf) ##
        buf=self._uart.readline()
        print(buf)  ##
        if not buf:
            return None
        result = _convert_to_string(buf)
        if lines>1:
            self.savbuf = ''
            for i in range(lines-1):
                buf=self._uart.readline()
                if not buf:
                    return result
                #print(buf)
                buf = _convert_to_string(buf)
                if not buf == '' and not buf == 'OK':
                    self.savbuf += buf+'\n'
        return result
    
    def setup(self):
        self.command(b'ATE0\n')         # command echo off
        self.command(b'AT+CRSL=99\n')   # ringer level
        self.command(b'AT+CMIC=0,10\n') # microphone gain
        self.command(b'AT+CLIP=1\n')    # caller line identification
        self.command(b'AT+CMGF=1\n')    # plain text SMS
        self.command(b'AT+CALS=3,0\n')  # set ringtone
        self.command(b'AT+CLTS=1\n')    # enabke get local timestamp mode
        self.command(b'AT+CSCLK=0\n')   # disable automatic sleep
        
    def wakechars(self):
        self._uart.write(b'AT\n')        # will be ignored
        utime.sleep_ms(100)
    
    def sleep(self,n):
        self.command(b'AT+CSCLK=T%d\n' % n)
            
    def sms_alert(self):
        self.command(b'AT+CALS=1,1\n')  # set ringtone
        utime.sleep_ms(3000)
        self.command(b'AT+CALS=3,0\n')  # set ringtone
  
    def call(self,numstr):
        self.command(b'ATD%s;\n' % numstr)
        
    def hangup(self):
        self.command(b'ATH\n')
        
    def answer(self):
        self.command(b'ATA\n')
    
    def set_volume(self,vol):
        if (vol>=0 and vol<=100):
            self.command(b'AT+CLVL=%d\n' % vol)
    
    def signal_strength(self):
        result = self.command(b'AT+CSQ\n',3)
        if result:
            params = result.split(',')
            if not params[0] == '':
                params2 = params[0].split(':')
                if params2[0]=='+CSQ':
                    x = int(params2[1])
                    if not x == 99:
                        return(math.floor(x/6+0.5))
        return 0
        
    def battery_charge(self):
        result = self.command(b'AT+CBC\n', 3, 1500)
        if result:
            params=result.split(',')
            if not params[0] == '':
                params2 = params[0].split(':')
                if params2[0]=='+CBC':
                    return int(params[1])
        return 0
        
    def network_name(self):   
        result = self.command(b'AT+COPS?\n',3)
        if result:
            params=result.split(',')
            if not params[0] == '':
                params2 = params[0].split(':')
                if params2[0]=='+COPS':
                    if len(params)>2:
                        names = params[2].split('"')
                        if len(names)>1:
                            return names[1]
        return ''


    def read_sms(self, id):
        result = self.command(b'AT+CMGR=%d\n' % id,99)
        if result:
            params=result.split(',')
            if not params[0] == '':
                params2 = params[0].split(':')
                if params2[0]=='+CMGR':
                    number = params[1].replace('"',' ').strip()
                    date   = params[3].replace('"',' ').strip()
                    time   = params[4].replace('"',' ').strip()
                    return  [number,date,time,self.savbuf]
        return None
    
    def send_sms(self, destno, msgtext):
        result = self.command(b'AT+CMGS="%s"\n' % destno, 99, 5000, msgtext+b'\x1A')
        if result and result=='>' and self.savbuf:
            params = self.savbuf.split(':')
            if params[0]=='+CUSD' or params[0] == '+CMGS':
                return 'OK'
        return 'ERROR'
    
    def check_credit(self):
        self.command(b'AT+CUSD=1,"*100#"\n')
    
    def get_credit(self):
        return self.credit
    
    def delete_sms(self,id):
        self.command(b'AT+CMGD=%d\n' % id,1)
                     
    def date_time(self):
        result = self.command(b'AT+CCLK?\n',3)
        if result:
            if result[0:5] == "+CCLK":
                return result.split('"')[1]
        return ''
        
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


    # http get command using gprs
    def http_get(self,url,apn="giffgaff.com"):
        resp = None
        rstate = 0
        proto, dummy, surl = url.split("/", 2)
        is_ssl = 0
        if  proto == "http:":
            is_ssl = 0
        elif proto == "https:":
            is_ssl = 1
        else:
            raise ValueError("Unsupported protocol: " + proto)
        try:
            # open bearer context
            res = self.command(b'AT+SAPBR=3,1,"Contype","GPRS"\n')
            _check_result(b"SAPBR 1: ", 'OK', res)
            res = self.command(b'AT+SAPBR=3,1,"APN","%s"\n' % apn)
            _check_result("SAPBR 2: ", 'OK', res)
            res = self.command(b'AT+SAPBR=1,1\n',1,2000)
            _check_result("SAPBR 3: ", 'OK', res)
            # now do http request
            res = self.command(b'AT+HTTPINIT\n',1)
            _check_result("HTTPINIT: ", 'OK', res)
            res = self.command(b'AT+HTTPPARA="CID",1\n')
            _check_result("HTTPPARA 1: ", 'OK', res)
            res = self.command(b'AT+HTTPPARA="URL","%s"\n' % surl)
            _check_result("HTTPPARA 2: ", 'OK', res)
            res = self.command(b'AT+HTTPSSL=%d\n' % is_ssl)
            _check_result("HTTPSSL: ", 'OK', res)
            res = self.command(b'AT+HTTPACTION=0\n')
            _check_result("HTTPACTION: ", 'OK', res)
            for i in range(20):  #limit wait to max 20 x readline timeout
                buf = self._uart.readline()
                if buf and not buf=='\r\n':
                    buf = _convert_to_string(buf)
                    #print(buf)
                    prefix,retcode,bts = buf.split(',')
                    rstate = int(retcode)
                    nbytes = int(bts)
                    break
            res = self.command(b'AT+HTTPREAD\n',1)
            buf = self._uart.read(nbytes)
            _check_result("HTTPACTION: ", '+HTTPREAD: {}'.format(nbytes), res)
            if buf[-4:] == 'OK\r\n':  # remove final OK if it was read
                buf = buf[:-4]
            resp = Response(buf)
        except SIM800LError as err:
            print(str(err))
        self.command(b'AT+HTTPTERM\n',1) # terminate HTTP task
        self.command(b'AT+SAPBR=0,1\n',1) # close Bearer context
        return resp


    def test(self):
        r = self.http_get('http://exploreembedded.com/wiki/images/1/15/Hello.txt')
        print(r.text)





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

