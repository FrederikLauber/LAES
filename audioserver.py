__author__ = "Frederik Lauber"
__copyright__ = "Copyright 2014"
__license__ = "GPL3"
__version__ = "0.5"
__maintainer__ = "Frederik Lauber"
__status__ = "Production"
__contact__ = "https://flambda.de/impressum.html"
import socketserver
from threading import Thread


class AudioExtenderHandler(socketserver.StreamRequestHandler):
    header = "ICY 200 OK\r\ncontent-type: audio/pcm\r\nIcy-Metadata: 1\r\nIcy-MetaInt: 8192\r\n\r\n".encode("ascii")
    metatext = "StreamTitle='Arkados Virtual Driver test stream';".encode("ascii")
    blocks = len(metatext) // 16 + 1
    metadata = chr(blocks).encode("ascii") + metatext
    metadata = metadata.ljust(blocks * 16 + 1, b"\x00")  # add 1 to include the data length byte

    def __init__(self, request, client_address, server):
        self.serve = server
        self.identifier = server.identifier_function(client_address)
        self.data = server.queuemanager.reg_output_queue(self.identifier)
        super().__init__(request, client_address, server)

    def handle(self):
        try:
            self.wfile.write(self.header)
            while True:
                self.wfile.write(self.data.get())
                self.wfile.write(self.metadata)
                self.rfile.flush()
        except (ConnectionResetError, ConnectionAbortedError):
            pass

    def finish(self):
        self.server.queuemanager.del_output_queue(self.identifier, self.data)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def setup_socket_server(local_host_ip, qm, identifier_function):
    server = ThreadedTCPServer((local_host_ip, 12200), AudioExtenderHandler)
    server.queuemanager = qm
    server.identifier_function = identifier_function
    thread = Thread(target=server.serve_forever)
    thread.daemon = True
    server.daemon_threads = True
    thread.start()

