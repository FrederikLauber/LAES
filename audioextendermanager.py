__author__ = "Frederik Lauber"
__copyright__ = "Copyright 2014"
__license__ = "GPL3"
__version__ = "0.5"
__maintainer__ = "Frederik Lauber"
__status__ = "Production"
__contact__ = "https://flambda.de/impressum.html"
import socket
from xml.etree import ElementTree as ET
import socketserver
import threading
import time



def _unified_ip_split(ip_string):
    ip_parts = ip_string.split(".")
    ip_parts = [ip.zfill(3) for ip in ip_parts]
    return ip_parts


class AudioExtender:
    def __init__(self, mac, ip, subnet, infourl, name, unknown):
        self.mac = mac
        tmp = _unified_ip_split(ip)
        self.ip = ".".join(tmp)
        self._hash = int("".join(tmp))
        self.subnet = subnet
        self.name = name
        self.infourl = infourl
        self.unknown = unknown
        self.server_status = None
        self.url_playing = None
        self.drop_count = None

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return self._hash == other.__hash__()

    def infos(self):
        print("Name: ", self.name)
        print("MAC: ", self.mac)
        print("IP: ", self.ip)
        print("InfoUrl: ", self.infourl)
        print("SUBNET: ", self.subnet)
        print("UNKNOWN: ", self.unknown)
        print("Server Status:", self.server_status)
        print("Url Playing", self.url_playing)
        print("Drop Count", self.drop_count)

    def update_status(self):
        port = 80
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.ip, port))
        sock.send("GET /sysinfo.html HTTP/1.0\r\n\r\n".encode("ascii"))
        data = sock.recv(1024)
        string = b""
        while len(data):
            string = string + data
            data = sock.recv(1024)
        sock.close()
        string = string[111:].decode("ascii")
        #statusside = urllib.request.urlopen(self.infourl)
        #data = statusside.read()
        #statusside.close()
        element = ET.XML(string)
        for sub in element:
            for subsub in sub:
                if subsub.tag is None:
                    pass
                elif subsub.tag.strip() == "server-status":
                    self.server_status = None if subsub.text is None else subsub.text.strip()
                elif subsub.tag == "url-playing":
                    self.url_playing = None if subsub.text is None else subsub.text.strip()
                elif subsub.tag == "drop-count":
                    self.drop_count = None if subsub.text is None else int(subsub.text.strip())

    def connectto(self, ip):
        port = 7060
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.ip, port))
        sock.send(("GET /streamer.cgi?cmd=srvstart HTTP/1.0\r\nX-Arkados-Url:\
        http://%s:12200\r\nX-Arkados-Cmd: http://%s:12201\r\n\r\n" % (ip, ip)).encode("ascii"))
        data = sock.recv(1024)
        string = b""
        while len(data):
            string = string + data
            data = sock.recv(1024)
        sock.close()
        return b"Stream command received" in string


def announce(local_ip):
    broadcast_ip = _unified_ip_split(local_ip)
    broadcast_ip[3] = "255"
    broadcast_ip = ".".join(broadcast_ip).encode("ascii")
    message = ('whoisthere\x00%s\x00255.255.255.0\x00' % local_ip).encode("ascii")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(message, (broadcast_ip, 19375))


class announceThread(threading.Thread):
    def __init__(self, local_ip, interval=60):
        super().__init__()
        self._stop = threading.Event()
        self.daemon = True
        self.broadcast_ip = _unified_ip_split(local_ip)
        self.broadcast_ip[3] = "255"
        self.broadcast_ip = ".".join(self.broadcast_ip).encode("ascii")
        self.message = ('whoisthere\x00%s\x00255.255.255.0\x00' % local_ip).encode("ascii")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.interval = interval

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        while not self._stop.isSet():
            self.sock.sendto(self.message, (self.broadcast_ip, 19375))
            self._stop.wait(self.interval)

class AudioExtenderBroadcastHandler(socketserver.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.server = server
        super().__init__(request, client_address, server)

    def handle(self):
        if self.request[0].startswith("hello".encode("ascii")):
            with self.server.lock:
                (hello, name, mac, ip, subnet, infourl, unknown, foo) = \
                    (item.decode("ascii") for item in self.request[0].split(b"\x00"))
                if not ip in self.server.ips_seen.keys():
                    ip_unified = ".".join(_unified_ip_split(ip))
                    tmp = AudioExtender(mac, ip, subnet, infourl, name, unknown)
                    self.server.audioextenders.add(tmp)
                    self.server.added_extender.set()
                    self.server.added_extender.clear()
                self.server.ips_seen[ip] = time.ctime()



class AudioExtenderManager(socketserver.ThreadingMixIn, socketserver.UDPServer):
    def __init__(self, server_ip, announce_interval=60):
        self.server_ip = server_ip
        self.audioextenders = set()
        self.ips_seen = {}
        self.lock = threading.Lock()
        self.announce = announceThread(server_ip, announce_interval)
        self.daemon_threads = True
        self.added_extender = threading.Event()
        super().__init__((server_ip, 19375), AudioExtenderBroadcastHandler)
        self.serv_thread = threading.Thread(target=self.serve_forever)
        self.serv_thread.daemon = True

    def start(self):
        self.serv_thread.start()
        self.announce.start()

    def stop(self):
        self.serv_thread.stop()
        self.announce.stop()


#class AutoconnectorEvent(threading.Thread):
#    def __init__(self, audioextendermanager, ip, timeout=None):
#        super().__init__(daemon=True)
#        self.audioextendermanger = audioextendermanager
#        self.ip = ip
#        self.timeout = timeout

#    def run(self):
#        while True:
#            for audioextender in self.audioextendermanger.audioextenders.copy():
#                try:
#                    audioextender.update_status()
#                    if audioextender.url_playing is None:# or not self.ip in audioextender.url_playing:
#                        audioextender.connectto(self.ip)
#                except Exception:
#                        continue
#            self.audioextendermanger.added_extender.wait(self.timeout)

class ThreadedUDPServer():
    pass


def list_all_found_devices():
    ip = socket.gethostbyname(socket.gethostname())
    aem = AudioExtenderManager(ip,10)
    aem.start()
    while True:
        print(len(aem.audioextenders))
        print(aem.audioextenders)
        for ae in aem.audioextenders:
            print(ae.infos())
        aem.added_extender.wait()

if __name__ == '__main__':
    list_all_found_devices()