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

	def __init__( self, application_name, max_bytes = 1024*100*10, backup_count = 100, delay = 3 ):
		self.logger = logging.getLogger(application_name)
		hdlr = logging.handlers.RotatingFileHandler(os.getcwd() + '/log/' + application_name + '.log', max_bytes, backup_count)
		formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
		hdlr.setFormatter(formatter)
		self.logger.addHandler(hdlr)
		self.logger.setLevel(logging.DEBUG)
		self.delay = delay
		Thread.__init__(self)

	def run( self ):
		while True:
			time.sleep(self.delay)
			self.lock_logger.acquire()
			for v in self.log_queue:
				if v[0] == 'Error':
					self.logger.error( str( v[1] ) )
				if v[0] == 'Info':
					self.logger.info( str( v[1] ) )
			del self.log_queue[:]				 
			self.lock_logger.release()

	def log( self, msg, code ):
		print(msg)
		self.lock_logger.acquire()
		if code == 'Info':
			self.log_queue.append( [ 'Info', msg ] )
		if code == 'Error':
			self.log_queue.append( [ 'Error', msg ] )
		self.lock_logger.release()
#=======================================================================================================