__author__ = "Frederik Lauber"
__copyright__ = "Copyright 2014"
__license__ = "GPL3"
__version__ = "0.5"
__maintainer__ = "Frederik Lauber"
__status__ = "Production"
__contact__ = "https://flambda.de/impressum.html"

import pyaudio
import configparser
import socket

def setup_what_you_hear(audio_device_index, qm):
    a = qm.reg_input_queue("WhatYouHear")
    def callback(in_data, frame_count, time_info, status):
        a.put(in_data)
        return in_data, pyaudio.paContinue
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=2,
        rate=44100,
        input=True,
        frames_per_buffer=2048,#this is 8192bytes, 2 Channels, 2 Bytes per sample, 2048 samples
        input_device_index=audio_device_index,
        stream_callback=callback)
    stream.start_stream()

def setup_and_get_info_from_config(config_name="LAES.conf"):
	config = configparser.ConfigParser()
	config.read(config_name)
	if not "LAES" in config:
		config["LAES"] = {}
	laes = config["LAES"]
	ip = laes.get("IP", socket.gethostbyname(socket.gethostname()))
	print("Assuming server is on ip: ", ip)
	audio = pyaudio.PyAudio()
	audio_device_index = laes.getint("audio_device_index", 0)
	audio_device_name = laes.get("audio_device_name", "saaad")
	checked_audio_device_name = audio.get_device_info_by_index(audio_device_index)['name']
	if audio_device_name != checked_audio_device_name:
		print("Config does not match the actual audio device")
		audio_device_index = None
		while audio_device_index is None:
			print("Please,choose the audio device, LAES.conf will be written automatically")
			for i in range(audio.get_device_count()):
				print(str(i), ": ", audio.get_device_info_by_index(i)['name'])
			tmp = int(input('Which device should be used? Just type the number:'))
			if tmp <= audio.get_device_count():
				audio_device_index = tmp
				config.set("LAES", "audio_device_index", str(audio_device_index))
				config.set("LAES", "audio_device_name", audio.get_device_info_by_index(audio_device_index)['name'])
				with open(config_name, 'w') as configfile:
					config.write(configfile)
	audio.terminate()
	return (ip,audio_device_index)