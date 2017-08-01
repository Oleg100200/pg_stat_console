from threading import Thread
import threading
import logging
import logging.handlers
import os
import sys
import time
#=======================================================================================================
class PSCLogger( Thread ):
	logger = None
	delay = None
	log_queue = []
	lock_logger = threading.Lock()
	do_stop = False
	__instance = None

	@staticmethod
	def instance():
		if PSCLogger.__instance == None:
			PSCLogger("PSCLogger")
		return PSCLogger.__instance 
			
	def __init__( self, application_name, max_bytes = 1024*100*10, backup_count = 100, delay = 3 ):
		self.logger = logging.getLogger(application_name)
		parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
		hdlr = logging.handlers.RotatingFileHandler(parent_dir + '/log/' + application_name + '.log', max_bytes, backup_count)
		formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
		hdlr.setFormatter(formatter)
		self.logger.addHandler(hdlr)
		self.logger.setLevel(logging.DEBUG)
		self.delay = delay
		PSCLogger.__instance = self
		Thread.__init__(self)

	def run( self ):
		while True and not self.do_stop:
			time.sleep(self.delay)
			self.lock_logger.acquire()
			for v in self.log_queue:
				if v[0] == 'Error':
					self.logger.error( str( v[1] ) )
				if v[0] == 'Info':
					self.logger.info( str( v[1] ) )
			del self.log_queue[:]				 
			self.lock_logger.release()
		print("PSCLogger stopped!")

	def stop( self ):
		self.do_stop = True
			
	def log( self, msg, code ):
		print(msg)
		self.lock_logger.acquire()
		if code == 'Info':
			self.log_queue.append( [ 'Info', msg ] )
		if code == 'Error':
			self.log_queue.append( [ 'Error', msg ] )
		self.lock_logger.release()
#=======================================================================================================