#!/usr/bin/python
# -*- coding: ascii -*-
#py -3.4 -m py2exe.build_exe myscript.py
#C:\Python34\Scripts\pyinstaller --onefile --console  --ascii AudioExtenderWhatYouHear.py

import socket
from threading import Thread
from queuemanager import QueueManager
from audioextendermanager import AudioExtenderManager, AudioExtender
from audioserver import setup_socket_server
from audiohelpers import setup_what_you_hear
import pyaudio
import time

class WaitforUserThread(Thread):
    def run(self):
        input("Press Enter to exit")
        print("Closing")

class AutoconnectionEvent(Thread):
    def __init__(self, audioextendermanager, ip, timeout=60):
        super().__init__(daemon=True)
        self.audioextendermanger = audioextendermanager
        self.ip = ip
        self.timeout = timeout

    def run(self):
        while True:
            for audioextender in self.audioextendermanger.audioextenders.copy():
                try:
                    audioextender.update_status()
                    if audioextender.url_playing is None:# or not self.ip in audioextender.url_playing:
                        audioextender.connectto(self.ip)
                except Exception:
                    continue
            time.sleep(self.timeout)


def autoconnect_to_OneQueue():
    local_host_ip = socket.gethostbyname(socket.gethostname())
    audio = pyaudio.PyAudio()
    #audio_device_index = 28
    for i in range(audio.get_device_count()):
        print(str(i), ": ", audio.get_device_info_by_index(i)['name'])
    audio_device_index = int(input('Which device should be used? Just type the number: '))
    qm = QueueManager()
    aem = AudioExtenderManager(local_host_ip, 60)
    aem.start()
    setup_what_you_hear(audio_device_index, qm)
    def id_func(client_ip):
        #every client gets what you hear
        return "WhatYouHear"
    setup_socket_server(local_host_ip, qm, id_func)
    t = WaitforUserThread()
    #give the audioextender some time to pick up all exteners on the netweok
    time.sleep(5)
    autoconnect = AutoconnectionEvent(aem, local_host_ip, 60)
    autoconnect.start()
    t.start()

if __name__ == '__main__':
    autoconnect_to_OneQueue()