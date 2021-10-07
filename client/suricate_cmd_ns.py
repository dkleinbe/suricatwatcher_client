from __future__ import annotations
import logging
import base64
from time import sleep
import io
import socketio
from socketio import namespace 
from gpiozero import CPUTemperature, LoadAverage
import numpy as np
from ultrasonic import Ultrasonic
from ADC import Adc

from suricate import Suricate
from camera_pi2 import Camera

import typing
if typing.TYPE_CHECKING:
	from suricate_client import Client

logger = logging.getLogger('suricate_client.' + __name__)

class SuricateCmdNS(socketio.ClientNamespace):

	logger.debug('class SuricateCmdNS')
	
	connection_count = 0

	def __init__(self, namespace, suricate_client : Client):

		logger.info("+ Init SuricateCmdNS")

		super(socketio.ClientNamespace, self).__init__(namespace)
		
		self.suricate_client = suricate_client
		self.suricate = None
		self.is_connected = False

	def on_connect_error(self, data):
		logger.critical("Connection error")

	def on_connect(self):
		
		SuricateCmdNS.connection_count += 1

		logger.info("+ %s: connection: %d", self.namespace, SuricateCmdNS.connection_count)

		cpu = CPUTemperature()
		loadavg = LoadAverage()
		ultrasonic = Ultrasonic() 
		adc = Adc()

		self.is_connected = True
		suricate_data = {}
		while self.is_connected:
			
			if self.suricate is not None and self.suricate.stream_video is True:
				with io.open(loadavg.load_average_file, 'r') as f:

					file_columns = f.read().strip().split()
					load = float(file_columns[loadavg._load_average_file_column])
				distance = ultrasonic.get_distance()
				left_sensor, right_sensor = adc.get_photosensors()
				power = adc.get_power()

				logger.info("+ CPU Temp: %.2f, CPU load: %.2f Distance: %.2f", cpu.temperature, load, distance)
				logger.info("+ Left sensor: %.2f, Right sensor: %.2f | delta %.2f", left_sensor, right_sensor, abs(left_sensor - right_sensor))
				logger.info("+ Power: %.2f V", power)

				suricate_data['id'] = self.suricate.suricate_id
				suricate_data['cpu_temp'] = cpu.temperature
				suricate_data['cpu_load'] = load
				suricate_data['distance_sensor'] = distance
				suricate_data['light_sensor'] = {'left' : left_sensor, 'right' : right_sensor}
				suricate_data['battery_power'] = power

				self.suricate_client.sio.emit('suricate_data', suricate_data , '/suricate_cmd')

			sleep(1)



	def on_disconnect(self):

		SuricateCmdNS.connection_count -= 1

		logger.info("+ %s: disconnect: %d", self.namespace, SuricateCmdNS.connection_count)

		self.is_connected =False
		#
		# if we were streaming, free the camera
		#
		if self.suricate is not None:
			self.suricate.stop_video_stream()	

	def on_suricate_id(self, msg):

		logger.info("+ Recieved suricate_id")
		# TODO: move suricate to Client: self.suricate_client.suricate = ...
		self.suricate = Suricate(msg['suricate_id'], self.suricate_client.sio)

	def on_start_video_stream(self, data):
		
		logger.info("+ Recieved start_video_stream")

		if self.suricate is not None:
			self.suricate.start_video_stream()

	def on_stop_video_stream(self, data):
		
		logger.info("+ Recieved stop_video_stream")

		if self.suricate is not None:
			self.suricate.stop_video_stream()


	def on_start_cam_ctrl(self, data):

		logger.info("+ Recieved start cam ctrl")

		if self.suricate is not None:
			self.suricate.start_cam_ctrl()

	def on_stop_cam_ctrl(self, data):

		logger.info("+ Recieved stop cam ctrl")

		if self.suricate is not None:
			self.suricate.stop_cam_ctrl()

	def on_move_cam(self, vector):
		
		logger.debug("+ Recieved move_cam x: %.4f y: %.4f", vector['x'], vector['y'])
		
		if self.suricate is not None:
			self.suricate.move_cam(vector)
		



