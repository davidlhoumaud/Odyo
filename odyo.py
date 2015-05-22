#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys, os, time, thread, socket, commands
import glib, gobject
import pygst
import gst

class CLI_Main:
    
    def __init__(self):
        self.player = gst.element_factory_make("playbin2", "player")
        if "jack" in sys.argv[len(sys.argv)-1]:
            out = gst.element_factory_make("jackaudiosink", "out")
            self.player.add(out)
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
        
    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.playmode = False
        elif t == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.playmode = False
            
    def query_position(self):
        "Returns a (position, duration) tuple"
        try:
            position, format = self.player.query_position(gst.FORMAT_TIME)
        except:
            position = gst.CLOCK_TIME_NONE
        try:
            duration, format = self.player.query_duration(gst.FORMAT_TIME)
        except:
            duration = gst.CLOCK_TIME_NONE
        return (position, duration)
        
    def pause(self):
        gst.info("pausing...")
        self.player.set_state(gst.STATE_PAUSED)
        self.playmode = True

    def play(self):
        gst.info("playing...")
        self.player.set_state(gst.STATE_PLAYING)
        #Start FadeIn
        if len(sys.argv) > 3:
            if float(sys.argv[3]) > 0:
                self.player.set_property('volume', 0)
                self.FadeIn(float(sys.argv[3]),1)
            else:
                self.player.set_property('volume', 1)
        else:
            self.player.set_property('volume', 1)
        #End FadeIn
        
    def stop(self):
        #FadeOut
        if len(sys.argv) > 3:
            if float(sys.argv[4]) > 0:
                self.FadeOut(float(sys.argv[4]),0)
            else:
                self.player.set_property('volume', 0)
        else:
            self.player.set_property('volume', 0)
        #End FadeOut
        gst.info("stopped")
        self.player.set_state(gst.STATE_NULL)
        self.playmode = False
    
    def seek(self, location):
        gst.debug("seeking to %r" % location)
        event = gst.event_new_seek(1.0, gst.FORMAT_TIME,
            gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
            gst.SEEK_TYPE_SET, location,
            gst.SEEK_TYPE_NONE, 0)

        res = self.player.send_event(event)
        if res:
            gst.info("setting new stream time to 0")
            self.player.set_new_stream_time(0L)
        else:
            gst.error("seek to %r failed" % location)
            
    def volume(self, vol):
        self.player.set_property("volume", vol)

    def convert_ns(self, t, a):
        # This method was submitted by Sam Mason.
        # It's much shorter than the original one.
        #temps restant
        _rms = (a/1000000)-(t/1000000)
        rs = (a/1000000000)-(t/1000000000)
        rm,rs = divmod(rs, 60)
        if rm < 60:
            _rest="%i;%02i:%02i" %(_rms,rm,rs)
        else:
            rh,rm = divmod(rm, 60)
            _rest="%i;%i:%02i:%02i" %(_rms,rh,rm,rs)
            
        #temps écoulé
        _ms = t/1000000
        s,ns = divmod(t, 1000000000)
        m,s = divmod(s, 60)
        if m < 60:
            _ecoul="%i;%02i:%02i|%s" %(_ms,m,s,_rest)
        else:
            h,m = divmod(m, 60)
            _ecoul="%i;%i:%02i:%02i|%s" %(_ms,h,m,s,_rest)
            
        #temps total
        _ms = a/1000000
        s,ns = divmod(a, 1000000000)
        m,s = divmod(s, 60)
        if m < 60:
            return "%s|%i;%02i:%02i" %(_ecoul,_ms,m,s)
        else:
            h,m = divmod(m, 60)
            return "%s|%i;%i:%02i:%02i" %(_ecoul,_ms,h,m,s)
    
    def FadeIn(self, seconds, to):
        i=self.player.get_property('volume')
        while i < to:
            i+=0.001
            self.player.set_property('volume', i)
            time.sleep(seconds/1000)
    
    def FadeOut(self, seconds, to):
        i=self.player.get_property('volume')
        while i > to:
            i-=0.001
            if i > -0.000000:
                self.player.set_property('volume', i)
            else:
                break
            time.sleep(seconds/1000)
    
    def start(self):
        if os.path.isfile(sys.argv[2]) or 'http://' in sys.argv[2]:
            # Create a TCP/IP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if "host=" in sys.argv[len(sys.argv)-1]:
                self.server_name = sys.argv[len(sys.argv)-1].split('=')[1].split(':')[0]
                _port = sys.argv[len(sys.argv)-1].split('=')[1].split(':')[1]
                if self.server_name == "default":
                    self.server_name = commands.getoutput("ifconfig").split("\n")[1].split()[1][4:]
            else:
                self.server_name="localhost"
                _port=3309
            self.server_address = (self.server_name, int(_port))
            self.sock.bind(self.server_address)
            self.sock.listen(1)
            # END Create a TCP/IP socket
            if 'http://' in sys.argv[2]:
                self.player.set_property("uri", sys.argv[2])
            else:
                self.player.set_property("uri", "file://" + sys.argv[2])
            self.p_position = gst.CLOCK_TIME_NONE
            self.p_duration = gst.CLOCK_TIME_NONE
            print "Server "+self.server_name+":"+str(_port)+" started"
            self.playmode = True
            self.play()
            
            
            _PAUSE=False
            while self.playmode:
                self.connection, self.client_address = self.sock.accept()
                data = self.connection.recv(100)
                _data = data.split(' ')

                print str(self.client_address)+" > "+str(data)
                if _data[0] == 'pause':
                    if _PAUSE:
                        _PAUSE=False
                        self.play()
                    else:
                        _PAUSE=True
                        self.pause()
                elif _data[0] == 'stop':
                    self.stop()
                elif _data[0] == 'seek':
                    self.seek(int(_data[1]))
                elif _data[0] == 'volume':
                    self.volume(float(_data[1]))
                elif _data[0] == 'fade':
                    if float(_data[1]) > self.player.get_property('volume'):
                        self.FadeIn(float(_data[2]),float(_data[1]))
                    else:
                        self.FadeOut(float(_data[2]),float(_data[1]))
                elif _data[0] == 'getvolume':
                    _vol=str(self.player.get_property('volume')).strip()
                    self.connection.sendall(_vol)
                elif _data[0] == 'filename':
                    self.connection.sendall(sys.argv[2])
                elif _data[0] == 'position':
                    self.p_position, self.p_duration = self.query_position()
                    self.connection.sendall(self.convert_ns(self.p_position,self.p_duration))
                self.connection.close()
                    
        time.sleep(1)
        loop.quit()

######################################################################

def aide():
    print("""OdyO v0.2 GNU/GPL v3
by David Lhoumaud <craft@ckdevelop.org> 
USAGE:
    play            New player
        odyo play "/realpath/filename" <fadein> <fadeout>
        
    pause           Pause player
        odyo pause
        
    stop            Stop player
        odyo stop
        
    seek            Seek in player
        odyo seek <milliseconds>
        
    volume          Set volume player
        odyo volume <0-100>
        
    filename            Current filename
        odyo filename
            return: "/realpath/filename"
        
    position        Display current position
        odyo position 
            return: <position>""")
    sys.exit()

# TCP/IP socket
def GetClientControl(message, sock):
    amount_received = 0
    amount_expected = len(message)
    
    while amount_received < amount_expected:
        data = sock.recv(16384).strip()
        if message == "getvolume":
            amount_received += amount_expected
        else:
            amount_received += len(data)
        print data
    
def ClientControl(message,_GET):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if "host=" in sys.argv[len(sys.argv)-1]:
        _host = sys.argv[len(sys.argv)-1].split('=')[1].split(':')[0]
        _port = sys.argv[len(sys.argv)-1].split('=')[1].split(':')[1]
        if _host == "default":
            _host = commands.getoutput("ifconfig").split("\n")[1].split()[1][4:]
    else:
        _host="localhost"
        _port=3309
        
    server_address = (_host,int(_port))
    sock.connect(server_address)
    try:
        sock.sendall(message)
        if _GET:
            GetClientControl(message, sock)
    finally:
        sock.close()
    sys.exit()


filedir=os.path.expanduser("~" )+"/.odyo/"
if not os.path.exists(filedir):
    os.mkdir(filedir)

if len(sys.argv) < 2:
    aide()
#SET
if sys.argv[1] == "play":
    mainclass = CLI_Main()
    thread.start_new_thread(mainclass.start, ())
    gobject.threads_init()
    loop = glib.MainLoop()
    loop.run()
    
elif sys.argv[1] == "pause":
    ClientControl(sys.argv[1], False)
elif sys.argv[1] == "stop":
    ClientControl(sys.argv[1], False)
elif sys.argv[1] == "seek":
    ClientControl(sys.argv[1]+' '+str(int(sys.argv[2])*100000), False)
elif sys.argv[1] == "volume":
    if len(sys.argv) > 2:
        ClientControl(sys.argv[1]+' '+str(float(sys.argv[2])/100.000), False)
    else:
        ClientControl('getvolume', True)
elif sys.argv[1] == "fade":
    ClientControl(sys.argv[1]+' '+str(float(sys.argv[2])/100.000)+' '+sys.argv[3], False)
#GET
elif sys.argv[1] == "filename":
    ClientControl(sys.argv[1], True)
elif sys.argv[1] == "position":
    ClientControl(sys.argv[1], True)

else:
    aide()

