from threading import Thread
import threading
import postgresql
from datetime import datetime, timedelta
import os
import subprocess
import re
import time
import requests
import html 
import http.client
import json
import hashlib
import gzip
import locale
from operator import itemgetter
import json
import urllib.parse

import tornado.web
from tornado.ioloop import IOLoop
from concurrent.futures import ThreadPoolExecutor

from functools import partial

from sqlalchemy.pool import QueuePool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from contextlib import contextmanager

import configparser
from pgstatlogger import PSCLogger
from pgstatcommon.pg_stat_common import *

import errno
from socket import error as socket_error
#=======================================================================================================
current_dir = os.path.dirname(os.path.realpath(__file__)) + '/'
prepare_dirs(current_dir)
#=======================================================================================================
config = configparser.RawConfigParser()
config.optionxform = lambda option: option
config.read( current_dir + 'conf/pg_stat_console.conf')
#=======================================================================================================
limit_memory( 1024 * 1000 * int( read_conf_param_value( config['main']['application_max_mem'] ) ) )
#=======================================================================================================
EXECUTOR = ThreadPoolExecutor(max_workers=int( read_conf_param_value( config['main']['max_workers'] ) ))
#=======================================================================================================
users_rights = []			#format [user_name, rights]
for user_rights in config['users_rights']:
	users_rights.append( [ user_rights, read_conf_param_value( config['users_rights'][user_rights] ) ] )

users_list = []				#format [user_name, password, rights]
for user in config['users']: 
	users_list.append( [user, read_conf_param_value( config['users'][user] ), next(user_rights[1] for user_rights in users_rights if user_rights[0]==user) ] )

active_users = []
#=======================================================================================================
pool_size_conf = int( read_conf_param_value( config['main']['db_pool_size'] ) )
timezone_correct_time_backward = read_conf_param_value( config['main']['timezone_correct_time_backward'] )
timezone_correct_time_forward = read_conf_param_value( config['main']['timezone_correct_time_forward'] ) 

pg_stat_monitor_port = int( read_conf_param_value( config['main']['pg_stat_monitor_port'] ) )
#=======================================================================================================
db_pools = []
db_pools.append( [ 'sys_stat', create_engine( read_conf_param_value( config['sys_stat']['sys_stat'] ) + '?application_name=' + \
	read_conf_param_value( config['main']['application_name'] ), pool_size=pool_size_conf, max_overflow=0, poolclass=QueuePool, \
	pool_recycle=int(read_conf_param_value( config['main']['db_pool_recycle'] ) )) ] )

session_factorys = []
for pool in db_pools:
	session_factorys.append( [ pool[0], sessionmaker(bind=pool[1],autocommit=False) ] )

scoped_sessions = []
for session_factory in session_factorys:
	scoped_sessions.append( [ session_factory[0], scoped_session(session_factory[1]) ] )
#=======================================================================================================
users_dashboards = []
for user_dashboard in config['users_dashboards']: 
	params = [] 	#[ param, duration ]
	keys = read_conf_param_value( config['users_dashboards'][user_dashboard] ).split(';')
	for key in keys:
		tmp = key.split(',')[1]
		params.append( [key.split(',')[0],tmp.split('=')[1]] ) 
	users_dashboards.append( [user_dashboard,params] )
#=======================================================================================================
sys_stat_conn_str = read_conf_param_value( config['sys_stat']['sys_stat_conn_str_direct'] )
application_name = read_conf_param_value( config['main']['application_name'] ) 
time_zone = read_conf_param_value( config['main']['time_zone'] )
db_pg_stat = postgresql.open( sys_stat_conn_str )
db_pg_stat.execute( """set application_name = '""" + application_name + """'""" )
db_pg_stat.execute( """SET timezone = '""" + time_zone + """';""" )
enable_exception_catching = read_conf_param_value( config['main']['enable_exception_catching'], True )
#=======================================================================================================
nodes_and_hosts = []	#[ node, host ]

nodes_visibility = []	#[ user_name, [ node1, node2, ...] ]
for user in config['nodes_visibility']: 
	user_nodes = read_conf_param_value( config['nodes_visibility'][user] )
	user_nodes_list = []
	for v in user_nodes.split(','):
		user_nodes_list.append( v.strip() )
	nodes_visibility.append( [user, user_nodes_list] )
#=======================================================================================================
page_refresh_interval = read_conf_param_value( config['main'][ "page_refresh_interval" ] )
custom_params = {}
for param in config['custom_params']: 
	custom_params[ param ] = read_conf_param_value( config['custom_params'][param] )

hide_password_in_queries = read_conf_param_value( config['main']['hide_password_in_queries'], True )
hide_host_in_queries = read_conf_param_value( config['main']['hide_host_in_queries'], True )
port = int( read_conf_param_value( config['main']['port'] ) )
#=======================================================================================================
graph_colors = [ 	[ "dark blue", 		"rgba(0,29,164,0.8)" ],
					[ "green", 			"rgba(0,193,0,0.8)" ],
					[ "violet", 		"rgba(65,0,153,0.8)" ],
					[ "orange", 		"rgba(255,123,4,0.8)" ],
					[ "red", 			"rgba(241,15,3,0.8)" ],
					[ "light red", 		"rgba(253,75,66,0.8)" ],
					[ "yellow", 		"rgba(255,204,0,0.8)" ],
					[ "light green", 	"rgba(159,236,0,0.8)" ],
					[ "fuchsia", 		"rgba(254,29,170,0.8)" ],
					[ "aquamarine", 	"rgba(24,124,135,0.8)" ],
					[ "brown", 			"rgba(117,56,11,0.8)" ],
					[ "light brown", 	"rgba(176,85,17,0.8)" ],
					[ "pink",			"rgba(255,106,215,0.8)" ],
					[ "beige", 			"rgba(227,174,94,0.8)" ],
					[ "gray", 			"rgba(99,97,124,0.8)" ] ]

def get_color( name ):
	return next(graph_color[1] for graph_color in graph_colors if graph_color[0]==name)
	
color_map = [ 	['%user', get_color("dark blue")], ['%system', get_color("green")], ['%iowait', get_color("violet")], \
				['%nice', get_color("orange")], ['%steal', get_color("red")], ['%idle', get_color("yellow")],

				['rx_bytes', get_color("green") ], ['tx_bytes', get_color("yellow")], \
				['RX-OK', get_color("green") ], ['TX-OK', get_color("yellow")], \
				['RX-ERR', get_color("red") ], ['TX-ERR', get_color("light red")], \
				['RX-DRP', get_color("brown") ], ['TX-DRP', get_color("light brown") ], \
				['RX-OVR', get_color("fuchsia") ], ['TX-OVR', get_color("pink") ], \
				
				['disk_size_used', get_color("light red")],['disk_size_avail', get_color("light green")],['disk_size', get_color("green")], \
				
				['AccessShareLock', get_color("green")],['RowExclusiveLock', get_color("orange")],['ExclusiveLock', get_color("fuchsia")], \
				['ShareRowExclusiveLock', get_color("pink")], \
				['RowShareLock', get_color("dark blue")],['ShareLock', get_color("violet")],['AccessExclusiveLock', get_color("red")],\
				['RowShareUpdateExclusiveLock', get_color("yellow")], \

				['xact_commit_per_sec', get_color("green")], ['xact_rollback_per_sec', get_color("light red")], \
				
				['idle in transaction',get_color("yellow")],['idle',get_color("orange")],['active',get_color("green")],['waiting_conns', get_color("dark blue")], \
				
				["AppMem",get_color("green")], ["MemFree",get_color("light green")], ["Buffers",get_color("brown")],["SwapTotal",get_color("red")],\
				["SwapFree",get_color("fuchsia")], ["Dirty",get_color("aquamarine")],\
				["Shmem",get_color("pink")],["Slab",get_color("yellow")],["PageTables",get_color("dark blue")],["SwapCached",get_color("orange")],\
				["VmallocUsed",get_color("beige")], ["Inactive",get_color("gray")], ["Active(file)",get_color("light red")], ["Inactive(file)",get_color("gray")],

				['checkpoints_timed', get_color("green") ], ['checkpoints_req', get_color("pink")], \
				['checkpoint_write_time', get_color("beige") ], ['checkpoint_sync_time', get_color("aquamarine") ], \
				
				['buffers_checkpoint', get_color("green") ], ['buffers_clean', get_color("dark blue") ], ['maxwritten_clean', get_color("yellow") ], \
				['buffers_backend', get_color("beige") ], ['buffers_alloc', get_color("fuchsia") ], ['buffers_backend_fsync', get_color("violet") ],\
				
				[ "rrqm/s", get_color("orange") ], ["wrqm/s", get_color("brown") ], \
				[ "r/s", get_color("orange") ], ["w/s", get_color("brown") ],\
				[ "rsec/s", get_color("orange") ], ["wsec/s", get_color("brown") ],\

				['tup_inserted_per_sec', get_color("dark blue") ], ['tup_updated_per_sec', get_color("pink") ], ['tup_deleted_per_sec', get_color("red") ],\
				['tup_returned_per_sec', get_color("green") ], ['tup_fetched_per_sec', get_color("light green") ] ]
	
custom_graph_sort = [ '%user', '%system', '%nice', '%steal', '%idle', '%iowait', \
				"AppMem", "PageTables", "Buffers", "Shmem", "Active(file)", "Inactive(file)", "Slab", "MemFree", "SwapFree" ]
#=======================================================================================================
admin_methods = [ 'stopQuery', 'downloadLogFile' ]
#=======================================================================================================
create_lock( current_dir, application_name )
#=======================================================================================================
logger = PSCLogger( application_name )
logger.start()
#=======================================================================================================
pattern = "^.*\.(gz)$"
for root, dirs, files in os.walk(current_dir + "download"):
	for file in filter(lambda x: re.match(pattern, x), files):
		os.remove(os.path.join(root, file))
		logger.log( "Unused file " + os.path.join(root, file), "Info" )
#=======================================================================================================
def stop_query( query_pid ):
	global db_pg_stat
	res = None
	try:
		query_get_data = db_pg_stat.prepare( 'select pg_cancel_backend(' + str( query_pid ) + ')' )
		res = query_get_data()
	except Exception as e:
		logger.log( str( e ) + " Connection error! Try reconnecting...", "Error" )
		time.sleep(10)
		try:
			db_pg_stat = postgresql.open( sys_stat_conn_str )
			db_pg_stat.execute( """set application_name = '""" + application_name + """'""" )
			db_pg_stat.execute( """SET timezone = '""" + time_zone + """';""" )
		except Exception as e:
			logger.log( "Reconnection error!", "Error" )
	return res[0][0]
#=======================================================================================================
class CoreHandler():
	session = None
	db_pid = None
	current_user = None
	current_user_dbs = None
	current_user_devices = None
	
	def __init__(self):
		self.current_user = []
		self.current_user_dbs = []
		self.current_user_devices = []
	
	@contextmanager
	def closing(self, session):
		try:
			yield session
		except postgresql.exceptions.QueryCanceledError:
			logger.log( "postgresql.exceptions.QueryCanceledError", "Error" )
			raise
			
		except ValueError as e:
			logger.log( str( e ), "Error" )
			raise
			
		except Exception as e:
			logger.log( str( e ), "Error" )
			raise
			
		finally:
			#logger.log( "call finally closing session", "Info" )
			session.close()	

	def get_current_user_name( self ):
		if len( self.current_user ) > 0:
			return self.current_user[0][1]
		else:
			return 'unknown_user'

	def get_current_user_rights( self ):
		user_name = self.get_current_user_name()
		for user in users_list:
			if user[0] == user_name:
				return user[2]
		return 'none'

	def get_current_user_nodes_visibility( self ):
		global nodes_visibility
		user_name = self.get_current_user_name()
		user_in_nv = False
		for nv in nodes_visibility:
			if user_name == nv[0]:
				user_in_nv = True

		if user_in_nv:
			return next(node[1] for node in nodes_visibility if node[0]==user_name)
		return []

	def check_auth( self ):
		params = tornado.escape.json_decode(self.request.body)
		if not ( 'user_auth_data' in params and params[ "user_auth_data" ] is not None ):
			return False

		user_auth_data = tornado.escape.json_decode(params[ "user_auth_data" ])
		#{\"param_name\":\"aggregator_raw\",\"node_name\":\"DB4 TC Apps Tapcore, Pixel Gun 3D\",\"param_type\":\"db_in_report\"}
		
		user_name = ""
		user_hash = ""
		selected_node_name = ""

		for v in user_auth_data:
			if v["param"] == "user_name" and "value" in v:
				user_name = v["value"]
			if v["param"] == "user_hash" and "value" in v:
				user_hash = v["value"]
			if v["param"] == "selected_node_name" and "value" in v:
				selected_node_name = v["value"]
		
		user_exists = False
		for active_user in active_users:
			if active_user[0] == user_hash:
				user_exists = True
				del self.current_user[:]
				self.current_user.append( [user_hash, user_name] )
		
		if user_exists == False:
			result_query = self.make_query( 'sys_stat', """select exists( SELECT 1 FROM public.psc_user_hashes where user_hash = '""" + user_hash + """') as res""", None, False )
			for row in result_query:
				user_exists = row['res']
				if user_exists:
					active_users.append( [user_hash, user_name] )
					del self.current_user[:]
					self.current_user.append( [user_hash, user_name] )	
		
		if user_exists == False:
			logger.log( "Invalid User " + str( user_hash ), "Error" )
			return False

		if 'user_config' in params and params[ "user_config" ] is not None:
			user_config = tornado.escape.json_decode(params[ "user_config" ])
			for v in user_config:
				if v["param_type"] == "device_in_report" and v["node_name"] == selected_node_name:
					self.current_user_devices.append( [v["node_name"], v["param_name"]] )
				if v["param_type"] == "db_in_report" and v["node_name"] == selected_node_name:
					self.current_user_dbs.append( [v["node_name"],v["param_name"]] )

		return True

	def make_query( self, db_name, query_text, node_name = None, need_auth = True ):
		global scoped_sessions
		list = []
		
		if len( self.current_user ) == 0:
			if need_auth and self.check_auth() == False:
				return []
		
		if node_name is not None and ( node_name == '' or node_name == 'null' ):
			logger.log( "call make_query(" + self.__class__.__name__  + "), invalid node_name, user = " + ( self.current_user[0][1] if need_auth else "unauth_user" ), "Error" )
			return []
			
		unv = self.get_current_user_nodes_visibility()
		if node_name is not None and node_name not in unv and len( unv ) > 0:
			logger.log( "call make_query(" + self.__class__.__name__  + "), node = '" + str( node_name ) + "' not allowed for user = " + ( self.current_user[0][1] if need_auth else "unauth_user" ), "Error" )
			return []
		
		self.session = next(scoped_session[1] for scoped_session in scoped_sessions if scoped_session[0]==db_name)
		
		with self.closing( self.session ) as session:
			session.execute( """set application_name = '""" + application_name + """'""" )
			session.execute( """SET timezone = '""" + time_zone + """';""" )
			if db_name == 'sys_stat' and node_name is not None:
				result_node = session.execute( """SELECT id FROM public.psc_nodes where node_name = '""" + node_name + """'""" )
				schema_id = None
				for row in result_node:
					schema_id = row['id']
				session.execute( """set search_path = 'n""" + str( schema_id ) + """', 'public';""" )

			backend_pid = session.execute( """select pg_backend_pid() as pid""" )
			for row in backend_pid:
				self.db_pid = row['pid']

			logger.log( "call make_query(" + self.__class__.__name__  + "), db_name = " + db_name + ", node_name = " + str(node_name) + \
				", user = " + ( self.current_user[0][1] if need_auth else "unauth_user" ) + " (" + \
				( str( self.current_user[0][0] )[:8] if need_auth else "no hash" ) + "), db_pid = " + str( self.db_pid ), "Info" )
			
			list = session.execute( query_text )
			session.commit()
		return list

	def on_connection_close(self):
		if self.db_pid is not None:
			logger.log( "stop_query = " + str( stop_query( self.db_pid ) ), "Info" )
			
	def get_pg_stat_monitor_host(self, node_name):
		global nodes_and_hosts
		
		for v in nodes_and_hosts:
			if v[0] == node_name:
				return v[1] + ":" + str(pg_stat_monitor_port)
				
		res = self.make_query( 'sys_stat', """SELECT node_host FROM public.psc_nodes where node_name = '""" + node_name + """'""", None, False )
		pg_stat_monitor_host = ""
		for v in res:
			pg_stat_monitor_host = v[0]
		nodes_and_hosts.append( [node_name, pg_stat_monitor_host] )
		return pg_stat_monitor_host + ":" + str(pg_stat_monitor_port)

	def proxy_http_post(self, method_name, timeout_p = 300 ):
		global admin_methods
		if self.check_auth() == False:
			return ""

		if method_name in admin_methods:
			if self.get_current_user_rights() != 'admin':
				logger.log( "No rights for call " + method_name, "Error" )
				return "No enougth rights"

		params = tornado.escape.json_decode(self.request.body) 
		if params[ "node_name" ] is None or params[ "node_name" ] == '' or params[ "node_name" ] == 'null':
			logger.log( "node_name is Null in proxy_http_post, method_name = " + method_name, "Error" )
			return ""
		
		try:
			monitor_host = self.get_pg_stat_monitor_host(params[ "node_name" ])
			h = http.client.HTTPConnection(monitor_host, timeout=timeout_p)
			
			dbs = []
			for db in self.current_user_dbs:
				dbs.append(db[1])
				
			post_params = {}
			for key, value in params.items():
				post_params[key] = value

			post_params["dbs"] = dbs

			logger.log( "call proxy_http_post(" + method_name + "), node_name = " + params[ "node_name" ] + ", monitor_host = " + monitor_host + ", user = " + \
					( self.current_user[0][1] ) + " (" + ( str( self.current_user[0][0] )[:8] ) + "), post_params = " + str( post_params["dbs"] ), "Info" )

			h.request( "POST", '/' + method_name, json.dumps(post_params, ensure_ascii=False).encode('utf8'), {'Content-Type': 'application/json'} )

			data_res = str(h.getresponse().read().decode( 'utf-8', 'ignore' ))
			h.close()
			return data_res
		except socket_error as serr:
			#ConnectionRefusedError: [Errno 111] Connection refused
			if serr.errno == errno.ECONNREFUSED:
				logger.log( "pg_stat_monitor not allowed, method_name = " + method_name, "Error" )
		
		logger.log( "pg_stat_monitor timeout " + str( timeout_p ) + " sec exceeded, method_name = " + method_name, "Error" )
		return "pg_stat_monitor not allowed"
		
	def get_pg_version(self):
		return self.proxy_http_post( 'getPGVersion', 3 )
		
class BaseAsyncHandlerNoParam(tornado.web.RequestHandler, CoreHandler):
	@tornado.web.asynchronous
	def get(self):
		def callback(future):
			if enable_exception_catching:
				try:
					self.write(future.result())
					self.finish()
				except Exception as e:
					self.clear()
					self.set_status(400)
					self.finish( str( e ) )
			else:
				self.write(future.result())
				self.finish()

		EXECUTOR.submit(
			partial(self.get_)
		).add_done_callback(
			lambda future: tornado.ioloop.IOLoop.instance().add_callback(
				partial(callback, future)))
			
	@tornado.web.asynchronous
	def post(self):
		def callback(future):
			if enable_exception_catching:
				try:
					self.write(future.result())
					self.finish()
				except Exception as e:
					self.clear()
					self.set_status(400)
					self.finish( str( e ) )
			else:
				self.write(future.result())
				self.finish()

		EXECUTOR.submit(
			partial(self.post_)
		).add_done_callback(
			lambda future: tornado.ioloop.IOLoop.instance().add_callback(
				partial(callback, future)))
	
class MainHandler(tornado.web.RequestHandler):
	def set_extra_headers(self, path):
		self.set_header("Cache-control", "cache")
	
	def get(self):
		self.render( current_dir + "main.html")

class PgStatConsoleStaticFileHandler(tornado.web.StaticFileHandler):
	def set_extra_headers(self, path):
		self.set_header('Cache-Control', 'store, cache, must-revalidate, max-age=0')

#=======================================================================================================
class GetUptimeHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getUptime', 3 )
		
class GetRefreshIntervalHandler(BaseAsyncHandlerNoParam):
	def get_(self):
		return page_refresh_interval
#=======================================================================================================
class GetOSParamValueHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		res = ""
		if schema_id is not None:
			result_query = None
			if data["device_name"] != 'null' and data["device_name"] != '':
				result_query = self.make_query( 'sys_stat', """
					SELECT round(""" + data["func"] + """(coalesce(val,0)), 3) as val_res
					FROM psc_os_stat s
					inner join psc_params p on p.id = s.param_id
					inner join psc_devices d on d.id = s.device_id and s.device_id is not null
					where p.param_name = '""" + data["param_name"] + """' and d.device_name = '""" + data["device_name"] + """' 
					and d.device_type = '""" + data["device_type"] + """' and dt >= '""" + data["date_a"] + """' and dt < '""" + data["date_b"] + """'""", data["node_name"], False )
			else:
				result_query = self.make_query( 'sys_stat', """
					SELECT round(""" + data["func"] + """(coalesce(val,0)), 3) as val_res
					FROM psc_os_stat s
					inner join psc_params p on p.id = s.param_id
					where p.param_name = '""" + data["param_name"] + """' and dt >= '""" + data["date_a"] + """' and dt < '""" + data["date_b"] + """'""", data["node_name"], False )

			for row in result_query:
				res = row['val_res']
		return str( res )
#=======================================================================================================
class LoginHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		global active_users
		global users_list

		data = tornado.escape.json_decode(self.request.body) 
		result = { "result": "fail", "user_hash": "none" }

		user_hash = ""
		user_name = ""
		login = False
		ip_addr = str( self.request.headers.get("X-Real-IP") if self.request.remote_ip == '127.0.0.1' else self.request.remote_ip )
		
		for user in users_list:
			if user[0] == data["login"] and user[1] == data["password"] and login == False:
				login = True
				user_hash =  str( data["login"] ) + "%" + str(data["password"]) + "%" + self.request.headers.get("User-Agent") + "%" + ip_addr
				user_hash = hashlib.sha256( user_hash.encode('utf-8') ).hexdigest()
				active_users.append( [ user_hash, user[0] ] )
				user_name = user[0]

		if login:
			result[ "result" ] = "ok"
			result[ "user_hash" ] = user_hash
			self.make_query( 'sys_stat', """select psc_get_user_hash('""" + str( user_hash ) + """', '""" + str( user_name ) + """','""" + \
				ip_addr + """','""" + str( self.request.headers.get("User-Agent") ) + """')""", None, False )
			logger.log( "Logged user: " + data["login"] + " User-Agent: " + self.request.headers.get("User-Agent") + " remote_ip: " + ip_addr, "Info" )

		self.set_header('Content-Type', 'application/json')
		return json.dumps(result, ensure_ascii=False).encode('utf8')

class UserHashHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		global active_users
		
		data = tornado.escape.json_decode(self.request.body) 
		result = { "result": "fail" }

		for user in active_users:
			if user[ 1 ] == data["user_name"] and user[ 0 ] == data["user_hash"]:
			   result[ "result" ] = "ok"
		self.set_header('Content-Type', 'application/json')
		return json.dumps(result, ensure_ascii=False).encode('utf8')
	
class GetCustomParamHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		result = { "result": "fail" }
		
		try:
			result[ "result" ] = custom_params[ data["param_name"] ]
		except Exception as e:
			result[ "result" ] = "undefined param name"
		
		self.set_header('Content-Type', 'application/json')
		return json.dumps(result, ensure_ascii=False).encode('utf8')
#=======================================================================================================
class Chart():
	global color_map
	def escapejs(self, val):
		return json.dumps(str(val))	
		
	def get_date_time_from_str(self, str_v ):
		time_v = re.findall(r"(\d{4})-(\d{2})-(\d{2})\s(\d{2}):(\d{2}):(\d{2})", str_v )[0]
		time_v_str = str( time_v[0] ) + "-" + str( time_v[1] ) + "-" + str( time_v[2] ) + " " + str( time_v[3] ) + ":" + str( time_v[4] ) + ":" + str( time_v[5] )	
		return time_v_str
			
	def exitst_dt_and_block(self, block_i, dt, data_copy ):
		for d in data_copy:
			if d[0] == block_i and str( d[1] ) == dt:
				return True
		return False
		
	def exitst_dt_and_line(self, line_name, dt, data_copy ):
		for d in data_copy:
			if d[3] == line_name and str( d[1] ) == dt:
				return True
		return False
				
	def remove_cred_data(self, query ):
		query_res = query
		if hide_password_in_queries:
			query_res = re.sub(r"password=\w+", '', query_res)	 
		if hide_host_in_queries:
			query_res = re.sub(r"host=\w+", '', query_res)
		return str( query_res )
		
	def make_stacked_chart(self, data, graph_name, chart_name ):
		#format data: [ [ block, datetime, value, ... ], ...] 	example:	[ [1,"2015-12-12 01:00:00+04",30668.2309999999998, ... ], ...]
		fields = []
		
		if not hasattr(data, 'keys'):
			return ""
			
		for k in data.keys():
			fields.append( k )	
		
		report_type = "unknown"
		
		if 'graph_block' in fields and 'dt_rounded' in fields and 'duration_sec' in fields and 'io_read_time_sec' in fields and \
			'total_read_blks_size_detail' in fields:
			report_type = "query_durations"

		if 'total_blks_size_detail' in fields:
			report_type = "query_blocks"

		if 'tbl_name' in fields:
			report_type = "simple_tbl_stat"
			
		if 'stm_query' in fields:
			report_type = "stm_query"
			
		graph_json = """""" 
		
		if report_type == "query_durations" or report_type == "query_blocks":
			graph_json += """function click_event( e )
			{
				$('.canvasjs-chart-tooltip').css("visibility", "hidden");
				
				$("#query_container").css('height', '200px');
				$("#explain_container").css('visibility', 'visible');
				
				$('#details').css("visibility", "visible");
				details_closed = false;	

				$('#query_container').empty();	
				$('#query_container').append( e.dataPoint.query );
				$('#explain_container').empty();	
				$('#explain_container').append( e.dataPoint.explain.replace(/ /g, "&nbsp;") );	
			}"""
			
		if report_type == "stm_query":
			graph_json += """function click_event( e )
			{
				$('.canvasjs-chart-tooltip').css("visibility", "hidden");
				
				$("#explain_container").css('visibility', 'hidden');
				$("#query_container").css('height', '530px');

				$('#details').css("visibility", "visible");
				details_closed = false;	
					
				$('#query_container').empty();	
				$('#query_container').append( e.dataPoint.stm_query );
			}"""
			
		graph_json += """	
			$('<div id=\"""" + chart_name + """\" class="scrollable_obj" style="height: 600px; width: 100%;" chart-name=\"""" + graph_name + """\"> </div>').appendTo( $('#graph_space' ) );
			var """ + chart_name + """ = new CanvasJS.Chart(\"""" + chart_name + """\",
			{
			  colorSet: "pscColors",
			  toolTip:{"""	

		if report_type == "query_durations" or report_type == "query_blocks":
			graph_json += """contentFormatter: function(e){
				  var content;
				  if( e.entries[0].dataPoint.detail_1 === 'none' ) 
					content = "<div style=\\"margin: 10px;\\"><strong>Date time: "+e.entries[0].dataPoint.label + "</strong></div><div style=\\"word-wrap: break-word;width: 500px;height: auto;margin: 10px;white-space: pre-wrap; */\\">"+ e.entries[0].dataPoint.query + "</div>";
				  else
				  if (typeof e.entries[0].dataPoint.detail_3 != 'undefined')
					content = "<div style=\\"margin: 10px;\\"><strong>Date time: "+e.entries[0].dataPoint.label + "</strong></div><div style=\\"margin: 10px;\\"><strong>"+e.entries[0].dataPoint.detail_1 + "</strong></div><div style=\\"margin: 10px;\\"><strong>"+e.entries[0].dataPoint.detail_2 + "</strong></div><div style=\\"margin: 10px;\\"><strong>"+e.entries[0].dataPoint.detail_3 + "</strong></div><div style=\\"word-wrap: break-word;width: 500px;height: auto;margin: 10px;white-space: pre-wrap; */\\">"+ e.entries[0].dataPoint.query + "</div>";			  
				  else
					content = "<div style=\\"margin: 10px;\\"><strong>Date time: "+e.entries[0].dataPoint.label + "</strong></div><div style=\\"margin: 10px;\\"><strong>"+e.entries[0].dataPoint.detail_1 + "</strong></div><div style=\\"word-wrap: break-word;width: 500px;height: auto;margin: 10px;white-space: pre-wrap; */\\">"+ e.entries[0].dataPoint.query + "</div>";			  
				  
				  return content;
				}"""
				
		if report_type == "simple_tbl_stat":
			graph_json += """content: function(e){
				  var content;
				  content = "<strong>"+e.entries[0].dataPoint.y + "</strong>" + " " + e.entries[0].dataPoint.tbl_name;
				  return content;
				}"""

		if report_type == "stm_query":
			graph_json += """content: function(e){
				  var content;
				  content = "<div style=\\"margin: 10px;\\"><strong>Date time: "+e.entries[0].dataPoint.label + "</strong></div><div style=\\"margin: 10px;\\"><strong>Total value: "+e.entries[0].dataPoint.y + "</strong></div><div style=\\"word-wrap: break-word;width: 500px;height: auto;margin: 10px;white-space: pre-wrap; */\\">"+ e.entries[0].dataPoint.stm_query + "</div>";
				  return content;
				}"""
				
		graph_json += """},	
			  animationEnabled: true,
			  zoomEnabled:true,
			  zoomType: "x",
			  animationDuration: 1300,
			  exportEnabled: true,
			  exportFileName: \"""" + graph_name + """\",
			  height:550,
			  title:{
				  text: \"""" + graph_name + """\",
				  fontSize: 16,
				  fontFamily: "Arial"
			  },  
				axisX:{	  
				   labelFontSize: 12,
				   labelAngle: -30,
				   labelFontFamily: "Arial"
				},
				axisY:{
					labelFontSize: 12
				},			
				data: [""";
		
		data_copy = []
		dt_points = []
		
		stacks_num = 0
		for v in data:
			data_copy.append( v )
			if v[ 0 ] > stacks_num:
				stacks_num = v[ 0 ]
				
		blocks = []	
		for i in range(1, stacks_num + 1):
			blocks.append( [] )
		
		for data in data_copy:
			if str( data[ 1 ] ) not in dt_points:
				dt_points.append( str( data[ 1 ] ) ) 
		
		for level_i in range(0, stacks_num ):
			for dt_point in dt_points:
				if self.exitst_dt_and_block( level_i + 1, dt_point, data_copy ):
					for d in data_copy:
						if d[0] == level_i + 1 and str( d[1] ) == dt_point:
							#--------------------------------------------------------------------------------------------------------------------------------
							if report_type == "query_durations":
								detail = "detail_1:\"\""
								if 'total_read_blks_size_detail' in fields and 'duration_sec' in fields and 'io_read_time_sec' in fields:
									detail = """  detail_1: \"""" + 'Loaded from disk: ' + str( d[ 'total_read_blks_size_detail' ] ) + """\"""" 
									detail += """,  detail_2: \"""" + 'I/O read time: ' + str( d[ 'io_read_time_sec' ] ) + """ sec\"""" 
									detail += """,  detail_3: \"""" + 'Duration: ' + str( d[ 'duration_sec' ] ) + """ sec\"""" 
								blocks[ level_i ].append( '{ y: ' + str( d[ 2 ] ) + ',  label: "' + self.get_date_time_from_str( str( d[ 1 ] ) ) + '",' + detail + \
								', query: ' + self.escapejs( self.remove_cred_data( str( d[ 'query' ] ) ) ).replace("\\n", "</br>") + ', explain: ' + self.escapejs( self.remove_cred_data( str( d[ 'plan' ] ) ) ).replace("\\n", "</br>") + '}' )	
							#--------------------------------------------------------------------------------------------------------------------------------
							if report_type == "query_blocks":
								detail = "detail_1:\"\""
								if 'total_blks_size_detail' in fields:
									detail = """  detail_1: \"""" + 'Value of calculated data: ' + str( d[ 'total_blks_size_detail' ] ) + """\"""" 
								blocks[ level_i ].append( '{ y: ' + str( d[ 2 ] ) + ',  label: "' + self.get_date_time_from_str( str( d[ 1 ] ) ) + '",' + detail + \
								', query: ' + self.escapejs( self.remove_cred_data( str( d[ 'query' ] ) ) ).replace("\\n", "</br>") + ', explain: ' + self.escapejs( self.remove_cred_data( str( d[ 'plan' ] ) ) ).replace("\\n", "</br>") + '}' )	
							#--------------------------------------------------------------------------------------------------------------------------------
							if report_type == "stm_query":
								detail = "detail_1:\"\""
								#if 'stm_query' in fields:
								#	detail = """  detail_1: \"""" + 'Loaded from disk: ' + str( d[ 'total_read_blks_size_detail' ] ) + """\"""" 
								#	detail += """,  detail_2: \"""" + 'I/O read time: ' + str( d[ 'io_read_time_sec' ] ) + """ sec\"""" 
								#	detail += """,  detail_3: \"""" + 'Duration: ' + str( d[ 'duration_sec' ] ) + """ sec\"""" 
								blocks[ level_i ].append( '{ y: ' + str( d[ 2 ] ) + ',  label: "' + self.get_date_time_from_str( str( d[ 1 ] ) ) + '",' + detail + \
								', stm_query: ' + self.escapejs( self.remove_cred_data( str( d[ 'stm_query' ] ) ) ).replace("\\n", "</br>") + '}' )	
							#--------------------------------------------------------------------------------------------------------------------------------
							if report_type == "simple_tbl_stat":
								detail = "tbl_name:\"" + str( d[ 'tbl_name' ] ) + "\""
								blocks[ level_i ].append( '{ y: ' + str( d[ 2 ] ) + ',  label: "' + self.get_date_time_from_str( str( d[ 1 ] ) ) + '",' + detail + '}' )
							
							if report_type == "unknown":
								blocks[ level_i ].append( '{ y: ' + str( d[ 2 ] ) + ',  label: "' + self.get_date_time_from_str( str( d[ 1 ] ) )  + '"}' )	 #basic usage
				else:		
					blocks[ level_i ].append( '{ y: 0,  label: "' +  self.get_date_time_from_str( str( dt_point ) ) + '"}' )
		
		blocks_txt = ""
		count_blk = 0

		for block in blocks:
			blocks_txt = blocks_txt + """{
			  click: function(e){
				click_event( e );
			},		
			type: "stackedColumn",
			markerType: "none",
			dataPoints: 
				["""
			
			block_len = len( block )
			block_pos = 0
			for v in block:
				blocks_txt = blocks_txt + v
				block_pos = block_pos + 1
				if block_pos < block_len:
					blocks_txt = blocks_txt + ","
				
			blocks_txt = blocks_txt + """]}"""
			
			count_blk = count_blk + 1
			if count_blk != stacks_num + 1:
				blocks_txt = blocks_txt +  ","

		graph_json = graph_json + blocks_txt + """]});""" + chart_name + """.render(); all_charts_on_page.push(""" + chart_name + """);"""
		return graph_json	
		
	def make_stacked_report(self, data, date = None ):
		html_report = """function show_graph() { """ 
			  
		id_container = 1

		for data_v in data:
			chart_name = data_v[ 1 ]
			if date is not None and len(date) == 2:
				chart_name += date[ 0 ]
				chart_name += date[ 1 ]
				
			chart_name = "chartContainer_" +  hashlib.md5(chart_name.encode()).hexdigest()
			html_report = html_report + str( self.make_stacked_chart( data_v[ 0 ], data_v[ 1 ], chart_name[:25] ) )
			id_container = id_container + 1
				
		html_report = html_report +  """} show_graph();"""
		return html_report		
		
	def make_line_chart(self, data, legend, graph_name, chart_name, graph_type ):
		#format data: [ [ block, datetime, value, ... ], ...] 	example:	[ [1,"2015-12-12 01:00:00+04",30668.2309999999998, ... ], ...]
		fields = []
		
		if not hasattr(data, 'keys'):
			return ""
		
		for k in data.keys():
			fields.append( k )	
		
		graph_json = """""" 

		graph_json += """	
			$('<div id=\"""" + chart_name + """\" class="scrollable_obj" style="height: 600px; width: 100%;" chart-name=\"""" + graph_name + """\"> </div>').appendTo( $('#graph_space' ) );
			var """ + chart_name + """ = new CanvasJS.Chart(\"""" + chart_name + """\",
			{
			  colorSet: "pscColors",
			  toolTip:{"""	

				
		graph_json += """},	
		
			legend:{
			   fontSize: 14,
				cursor: "pointer",
				fontFamily: "Arial",
				itemclick: function (e) {
					if (typeof (e.dataSeries.visible) === "undefined" || e.dataSeries.visible) {
						e.dataSeries.visible = false;
					} else {
						e.dataSeries.visible = true;
					}
					e.chart.render();
				}			   
			 },
			  animationEnabled: true,
			  zoomEnabled:true,
			  zoomType: "x",
			  animationDuration: 1300,
			  exportEnabled: true,
			  exportFileName: \"""" + graph_name + """\",
			  height:550,
			  title:{
				  text: \"""" + graph_name + """\",
				  fontSize: 16,
				  fontFamily: "Arial"
			  },  
				axisX:{  
				   labelFontSize: 12,
				   labelAngle: -30,
				   labelFontFamily: "Arial"
				},
				axisY:{
					labelFontSize: 12
				},
				data: [""";
		
		data_copy = []
		dt_points = []
		
		lines_num = 0
		lines_names = []
		
		legend_copy = []
		for v in legend:
			legend_copy.append( v )	
			
		for v in data:
			data_copy.append( v )
			if v[ 0 ] > lines_num:
				lines_num = v[ 0 ]
			if v[3] not in lines_names:
				lines_names.append(v[3])

		lines = []	
		for i in range(1, len( lines_names ) + 1):
			lines.append( [] )
		
		for data in data_copy:
			if str( data[ 1 ] ) not in dt_points:
				dt_points.append( str( data[ 1 ] ) ) 
		
		line_num = 0

		if len( lines_names ) > 0:
			if lines_names[0] in custom_graph_sort:
				lines_names.sort(key=lambda x: custom_graph_sort.index(x))
			else:
				lines_names.sort(reverse=False)
		else:
			lines_names.sort(reverse=False)
		
		
		for line_name in lines_names:
			for dt_point in dt_points:
				if self.exitst_dt_and_line( line_name, dt_point, data_copy ):
					for d in data_copy:
						if d[3] == line_name and str( d[1] ) == dt_point:
							lines[ line_num ].append( [ line_name, '{ y: ' + str( d[ 2 ] ) + ',  label: "' + self.get_date_time_from_str( str( d[ 1 ] ) )  + '", param: "' + d[ 3 ] + '"}' ] )
				else:
					lines[ line_num ].append( [ line_name, '{ y: 0,  label: "' +  self.get_date_time_from_str( str( dt_point ) ) + '"}' ] )
			line_num += 1
					
		blocks_txt = ""
		count_blk = 0
		for block in lines:
		
			if len( block ) < 1:
				continue
				
			legend_param = ""
			min_is_null = False
			for v in block:
				if v[1].find("param: \"") > -1:
					legend_param = re.findall( r"param:\s\"[^\"]*", v[1] )[0]
				else:
					min_is_null = True
			legend_param = legend_param[legend_param.find('"')+1:len(legend_param)]
			
			blocks_txt = blocks_txt + """{
			  click: function(e){
				click_event( e );
			},		
			type: \""""

			blocks_txt += graph_type + """\","""
	
			for elem in color_map:
				if block[0][0].find( '(' ) > 0:
					if block[0][0].find( '(' + elem[0] + ')' ) > -1:
						blocks_txt += """color: \"""" + elem[1] + """\","""
				else:
					if elem[0] == 'idle':   #exception param name: full compare
						if block[0][0] == elem[0]:
							blocks_txt += """color: \"""" + elem[1] + """\","""
					else:
						if block[0][0].find( elem[0] ) > -1:
							blocks_txt += """color: \"""" + elem[1] + """\","""

			legend_content = ""
			for legend in legend_copy:
				if legend[0] == legend_param:
					if min_is_null:
						legend_content = legend[0] + " " + re.sub( r'Min:\s[^\s]*', 'Min: 0.0,', legend[1] ) 
					else:
						legend_content = legend[0] + " " + legend[1]
			
			blocks_txt += """
			showInLegend: true,
			legendText: \"""" + legend_content + """\",
			markerType: "none",
			dataPoints: 
				["""
			
			block_len = len( block )
			block_pos = 0
			for v in block:
				blocks_txt = blocks_txt + v[1]
				
				block_pos = block_pos + 1
				if block_pos < block_len:
					blocks_txt = blocks_txt + ","

			blocks_txt = blocks_txt + """]}"""
			
			if count_blk <= lines_num:
				blocks_txt = blocks_txt +  ","

			count_blk = count_blk + 1
			
		graph_json = graph_json + blocks_txt + """]});""" + chart_name + """.render(); all_charts_on_page.push(""" + chart_name + """);"""
		return graph_json	
		
	def make_line_report(self, data, date = None ):
		html_report = """function show_graph() { """ 
			  
		id_container = 1

		for data_v in data:
			chart_name = data_v[ 2 ]
			if date is not None and len(date) == 2:
				chart_name += date[ 0 ]
				chart_name += date[ 1 ]
			
			chart_name = "chartContainer_" +  hashlib.md5(chart_name.encode()).hexdigest()	
			html_report = html_report + str( self.make_line_chart( data_v[ 0 ], data_v[ 1 ], data_v[ 2 ], chart_name[:25], data_v[ 3 ] ) )
			id_container = id_container + 1
				
		html_report = html_report +  """} show_graph();"""
		return html_report
#=======================================================================================================
class QueryMakerSimpleTblStat():
	def generate_query( self, db, dt_a, dt_b, param ):
		return """select row_number() OVER(PARTITION BY T.dt ORDER BY T.dt )  AS graph_block, * 
				from 
				(
				SELECT 	(s.dt """ + timezone_correct_time_backward +""")::timestamp without time zone as dt, s.val, t.tbl_name
					  FROM psc_tbls_stat s
					  inner join psc_dbs d on s.db_id = d.id
					  inner join psc_tbls t on s.tbl_id = t.id
					  inner join psc_params p on s.param_id = p.id
					  where d.db_name = '""" + db + """' and p.param_name = '""" + param + """' and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
						dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
					  order by s.dt asc,
					  s.val asc nulls last
					  
				) T order by T.dt asc, graph_block asc"""

class GetReadStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleTblStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []
		
		if self.check_auth() == False:
			return ""
			
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], \
					data[ "date_b" ], 'heap_blks_read_per_sec' ), data["node_name"] ), 'heap_blks_read_per_sec (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], \
					data[ "date_b" ], 'idx_blks_read_per_sec' ), data["node_name"] ), 'idx_blks_read_per_sec (' + db[1] + ')' ] )
				
		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class QueryMakerSimpleStat():
	def param_generator( self, param ):
		res_param = ""
		if param is not None:
			if type(param) is list:
				res_param = " in ("
				params_len = len( param )
				param_pos = 0
				for v in param:
					res_param = res_param + "'" + v + "'"
					param_pos = param_pos + 1
					if param_pos < params_len:
						res_param = res_param + ","
				if len( param ) == 0:
					res_param += "''"
				res_param += ")"
			else:
				res_param = " = '" + param + "'"	
		return res_param

	def generate_query( self, db, dt_a, dt_b, param ):
		return [ """	
			select row_number() OVER(PARTITION BY T.dt ORDER BY T.dt )  AS graph_block, * 
					from 
					(
						SELECT 	(s.dt """ + timezone_correct_time_backward +""")::timestamp without time zone as dt, round( val, 3), d.db_name || ' (' || p.param_name || ')'
						  FROM psc_dbs_stat s
						  inner join psc_params p on p.id = s.param_id
						  inner join psc_dbs d on d.id = s.db_id
						  where d.db_name """ + self.param_generator( db ) + """ and p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
							dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
						order by s.dt asc,
						s.val asc nulls last
					) T order by T.dt asc""", 
			"""
			select T.param, 'Avg: ' || T.avg_v::text || ', Min: ' || T.min_v::text || ', Max: ' || T.max_v::text from (
			SELECT d.db_name || ' (' || p.param_name || ')' as param, round( avg(val), 1) as avg_v, round( min(val), 1) as min_v, round( max(val), 1) as max_v
						  FROM psc_dbs_stat s
						  inner join psc_params p on p.id = s.param_id
						  inner join psc_dbs d on d.id = s.db_id
						  where d.db_name """ + self.param_generator( db ) + """ and p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
							dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
						group by param ) T""" ]
				
	def generate_query_common_stat( self, dt_a, dt_b, param, unit = None ):
		str_fld_calc = "val"
		if unit is not None:
			if unit == 'millisec_to_sec':
				str_fld_calc = "val / 1000"
			if unit == 'millisec_to_min':
				str_fld_calc = "val / 1000 * 60"
			if unit == 'blocks_to_mb':
				str_fld_calc = "(val * 8192 )/1048576"
			if unit == 'bytes_to_kb':
				str_fld_calc = "val / 1024"	
			if unit == 'bytes_to_mb':
				str_fld_calc = "val / 1048576"
				
		return [ """	
			select row_number() OVER(PARTITION BY T.dt ORDER BY T.dt )  AS graph_block, * 
					from 
					(
						SELECT 	(s.dt """ + timezone_correct_time_backward +""")::timestamp without time zone as dt, round( """ + str_fld_calc + """, 3), p.param_name
						  FROM psc_common_stat s
						  inner join psc_params p on p.id = s.param_id
						  where p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
							dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
						order by s.dt asc,
						s.val asc nulls last
					) T order by T.dt asc""", 
			"""
			select T.param, 'Avg: ' || T.avg_v::text || ', Min: ' || T.min_v::text || ', Max: ' || T.max_v::text from (
			SELECT p.param_name as param, round( avg(""" + str_fld_calc + """), 1) as avg_v, round( min(""" + str_fld_calc + """), 1) as min_v, round( max(""" + str_fld_calc + """), 1) as max_v
						  FROM psc_common_stat s
						  inner join psc_params p on p.id = s.param_id
						  where p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
							dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
						group by param ) T""" ]

	def get_os_devices( self, dt_a, dt_b, param ):
		return """SELECT d.device_name
							  FROM psc_os_stat s
							  inner join psc_params p on p.id = s.param_id
							  inner join psc_devices d on d.id = s.device_id
							  where p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
								dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
							group by d.device_name""" 	
	
	def generate_query_os_stat( self, dt_a, dt_b, device, param, unit = None ):
		str_fld_calc = "val"
		if unit is not None:
			if unit == 'millisec_to_sec':
				str_fld_calc = "val / 1000"
			if unit == 'millisec_to_min':
				str_fld_calc = "val / 1000 * 60"
			if unit == 'blocks_to_mb':
				str_fld_calc = "(val * 8192 )/1048576"
			if unit == 'bytes_to_kb':
				str_fld_calc = "val / 1024"
			if unit == 'bytes_to_mb':
				str_fld_calc = "val / 1048576"
				
		if device is not None:
			return [ """	
				select row_number() OVER(PARTITION BY T.dt ORDER BY T.dt ) AS graph_block, * 
						from 
						(
							SELECT 	(psc_round_minutes(s.dt, 5) """ + timezone_correct_time_backward +""")::timestamp without time zone as dt, round( """ + str_fld_calc + """, 3), d.device_name || ' (' || p.param_name || ')'
							  FROM psc_os_stat s
							  inner join psc_params p on p.id = s.param_id
							  inner join psc_devices d on d.id = s.device_id
							  where d.device_name """ + self.param_generator( device ) + """ and p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
								dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
							order by s.dt asc,
							s.val asc nulls last
						) T order by T.dt asc""", 
				"""
				select T.param, 'Avg: ' || T.avg_v::text || ', Min: ' || T.min_v::text || ', Max: ' || T.max_v::text from (
				SELECT d.device_name || ' (' || p.param_name || ')' as param, round( avg(""" + str_fld_calc + """), 1) as avg_v, round( min(""" + str_fld_calc + """), 1) as min_v, round( max(""" + str_fld_calc + """), 1) as max_v
							  FROM psc_os_stat s
							  inner join psc_params p on p.id = s.param_id
							  inner join psc_devices d on d.id = s.device_id
							  where d.device_name """ + self.param_generator( device ) + """ and p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
								dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
							group by param ) T""" ]
		else:
			return [ """	
				select row_number() OVER(PARTITION BY T.dt ORDER BY T.dt ) AS graph_block, * 
						from 
						(
							SELECT 	(psc_round_minutes(s.dt, 5) """ + timezone_correct_time_backward +""")::timestamp without time zone as dt, round( """ + str_fld_calc + """, 3), p.param_name
							  FROM psc_os_stat s
							  inner join psc_params p on p.id = s.param_id
							  where p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
								dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
							order by s.dt asc,
							s.val asc nulls last
						) T order by T.dt asc""", 
				"""
				select T.param, 'Avg: ' || T.avg_v::text || ', Min: ' || T.min_v::text || ', Max: ' || T.max_v::text from (
				SELECT p.param_name as param, round( avg(""" + str_fld_calc + """), 1) as avg_v, round( min(""" + str_fld_calc + """), 1) as min_v, round( max(""" + str_fld_calc + """), 1) as max_v
							  FROM psc_os_stat s
							  inner join psc_params p on p.id = s.param_id
							  where p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
								dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
							group by param ) T""" ]
							
	def generate_query_os_stat_in_gb( self, dt_a, dt_b, device, param ):
		if device is not None:
			return [ """	
				select row_number() OVER(PARTITION BY T.dt ORDER BY T.dt ) AS graph_block, * 
						from 
						(
							SELECT 	(psc_round_minutes(s.dt, 5) """ + timezone_correct_time_backward +""")::timestamp without time zone as dt, round( val * 0.000000954, 3), d.device_name || ' (' || p.param_name || ')'
							  FROM psc_os_stat s
							  inner join psc_params p on p.id = s.param_id
							  inner join psc_devices d on d.id = s.device_id
							  where d.device_name """ + self.param_generator( device ) + """ and p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
								dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
							order by s.dt asc,
							s.val asc nulls last
						) T order by T.dt asc""", 
				"""
				select T.param, 'Avg: ' || T.avg_v::text || ', Min: ' || T.min_v::text || ', Max: ' || T.max_v::text from (
				SELECT d.device_name || ' (' || p.param_name || ')' as param, ( select pg_size_pretty( round( avg(val), 1)::bigint * 1024 ) ) as avg_v, ( select pg_size_pretty( round( min(val), 1)::bigint * 1024 ) ) as min_v, ( select pg_size_pretty( round( max(val), 1)::bigint * 1024 ) ) as max_v
							  FROM psc_os_stat s
							  inner join psc_params p on p.id = s.param_id
							  inner join psc_devices d on d.id = s.device_id
							  where d.device_name """ + self.param_generator( device ) + """ and p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
								dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
							group by param ) T""" ]
		else:
			return [ """	
				select row_number() OVER(PARTITION BY T.dt ORDER BY T.dt ) AS graph_block, * 
						from 
						(
							SELECT 	(psc_round_minutes(s.dt, 5) """ + timezone_correct_time_backward +""")::timestamp without time zone as dt, round( val * 0.000000954, 3), p.param_name
							  FROM psc_os_stat s
							  inner join psc_params p on p.id = s.param_id
							  where p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
								dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
							order by s.dt asc,
							s.val asc nulls last
						) T order by T.dt asc""", 
				"""
				select T.param, 'Avg: ' || T.avg_v::text || ', Min: ' || T.min_v::text || ', Max: ' || T.max_v::text from (
				SELECT p.param_name as param, ( select pg_size_pretty( round( avg(val), 1)::bigint * 1024 ) ) as avg_v, ( select pg_size_pretty( round( min(val), 1)::bigint * 1024 ) ) as min_v, ( select pg_size_pretty( round( max(val), 1)::bigint * 1024 ) ) as max_v
							  FROM psc_os_stat s
							  inner join psc_params p on p.id = s.param_id
							  where p.param_name """ + self.param_generator( param ) + """ and dt >= '""" + dt_a + """'::timestamp """ + timezone_correct_time_forward +""" and 
								dt < '""" + dt_b + """'::timestamp """ + timezone_correct_time_forward + """ 
							group by param ) T""" ]

class GetCPUStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		queries = self.generate_query_os_stat( data[ "date_a" ], data[ "date_b" ], None, [ "%user", "%nice", "%system", "%iowait", "%steal", "%idle" ] )
		data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), 'CPU load, %', 'stackedArea' ] )

		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetMemUsageStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""		

		queries = self.generate_query_os_stat_in_gb( data[ "date_a" ], data[ "date_b" ], None, \
			[ "AppMem", "PageTables", "Buffers", "Shmem", "Active(file)", "Inactive(file)", "Slab", "MemFree", "SwapFree" ] )
				
		#AppMem + PageTables + Buffers + Shmem + Active(file) + Inactive(file) + Slab  + MemFree = MemTotal
		#Cached = Shmem + Active(file) + Inactive(file)
	
		data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), 'Memory usage, GB', 'stackedArea' ] )
			
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetDiskUtilStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		psc_devices = self.make_query( 'sys_stat', self.get_os_devices( data[ "date_a" ], data[ "date_b" ], [ "%util" ] ), data["node_name"] )
		for device in psc_devices:
			if [ data["node_name"], device[0] ] in self.current_user_devices:
				queries = self.generate_query_os_stat( data[ "date_a" ], data[ "date_b" ], device[0], [ "%util" ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'Disk utilization (' + device[0] + '), %', 'line' ] )
				
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetDiskUsageStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		psc_devices = self.make_query( 'sys_stat', self.get_os_devices( data[ "date_a" ], data[ "date_b" ], [ "disk_size_avail", "disk_size_used" ] ), data["node_name"] )
		for device in psc_devices:
			if [ data["node_name"], device[0] ] in self.current_user_devices:
				queries = self.generate_query_os_stat_in_gb( data[ "date_a" ], data[ "date_b" ], device[0], [ "disk_size_avail", "disk_size_used" ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'Disk usage (' + device[0] + '), GB', 'stackedArea' ] )
				
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetWRQMRRQMStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		psc_devices = self.make_query( 'sys_stat', self.get_os_devices( data[ "date_a" ], data[ "date_b" ], [ "rrqm/s", "wrqm/s" ] ), data["node_name"] )
		for device in psc_devices:
			if [ data["node_name"], device[0] ] in self.current_user_devices:
				queries = self.generate_query_os_stat( data[ "date_a" ], data[ "date_b" ], device[0], [ "rrqm/s", "wrqm/s" ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'rrqm/s wrqm/s (' + device[0] + '), requests', 'line' ] )
				
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetWRStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		psc_devices = self.make_query( 'sys_stat', self.get_os_devices( data[ "date_a" ], data[ "date_b" ], [ "r/s", "w/s" ] ), data["node_name"] )
		for device in psc_devices:
			if [ data["node_name"], device[0] ] in self.current_user_devices:
				queries = self.generate_query_os_stat( data[ "date_a" ], data[ "date_b" ], device[0], [ "r/s", "w/s" ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'r/s w/s (' + device[0] + '), requests', 'stackedArea' ] )
				
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetRSecWSecStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		psc_devices = self.make_query( 'sys_stat', self.get_os_devices( data[ "date_a" ], data[ "date_b" ], [ "rMB/s", "wMB/s" ] ), data["node_name"] )
		for device in psc_devices:
			if [ data["node_name"], device[0] ] in self.current_user_devices:
				queries = self.generate_query_os_stat( data[ "date_a" ], data[ "date_b" ], device[0], [ "rMB/s", "wMB/s" ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'rMB/s wMB/s (' + device[0] + '), MBytes', 'stackedArea' ] )
				
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetAVGRQStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		psc_devices = self.make_query( 'sys_stat', self.get_os_devices( data[ "date_a" ], data[ "date_b" ], [ "avgrq-sz" ] ), data["node_name"] )
		for device in psc_devices:
			if [ data["node_name"], device[0] ] in self.current_user_devices:
				queries = self.generate_query_os_stat( data[ "date_a" ], data[ "date_b" ], device[0], [ "avgrq-sz" ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'avgrq-sz (' + device[0] + '), sectors', 'line' ] )
				
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetAVGQUStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		psc_devices = self.make_query( 'sys_stat', self.get_os_devices( data[ "date_a" ], data[ "date_b" ], [ "avgqu-sz" ] ), data["node_name"] )
		for device in psc_devices:
			if [ data["node_name"], device[0] ] in self.current_user_devices:
				queries = self.generate_query_os_stat( data[ "date_a" ], data[ "date_b" ], device[0], [ "avgqu-sz" ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'avgqu-sz (' + device[0] + '), requests', 'line' ] )
				
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetAWaitStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		psc_devices = self.make_query( 'sys_stat', self.get_os_devices( data[ "date_a" ], data[ "date_b" ], [ "await" ] ), data["node_name"] )
		for device in psc_devices:
			if [ data["node_name"], device[0] ] in self.current_user_devices:
				queries = self.generate_query_os_stat( data[ "date_a" ], data[ "date_b" ], device[0], [ "await" ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'await (' + device[0] + '), milliseconds', 'line' ] )
				
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetNetworkTrafficStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		psc_devices = self.make_query( 'sys_stat', self.get_os_devices( data[ "date_a" ], data[ "date_b" ], [ "rx_bytes", "tx_bytes" ] ), data["node_name"] )
		for device in psc_devices:
			if [ data["node_name"], device[0] ] in self.current_user_devices:
				queries = self.generate_query_os_stat( data[ "date_a" ], data[ "date_b" ], device[0], [ "rx_bytes", "tx_bytes" ], 'bytes_to_kb' )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'rx_bytes tx_bytes (' + device[0] + '), kBytes/sec', 'stackedArea' ] )
				
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetNetworkPacketsStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		psc_devices = self.make_query( 'sys_stat', self.get_os_devices( data[ "date_a" ], data[ "date_b" ], [ "RX-OK", "TX-OK" ] ), data["node_name"] )
		for device in psc_devices:
			if [ data["node_name"], device[0] ] in self.current_user_devices:
				queries = self.generate_query_os_stat( data[ "date_a" ], data[ "date_b" ], device[0], [ "RX-OK", "TX-OK" ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'RX-OK TX-OK (' + device[0] + '), packets', 'stackedColumn' ] )
				
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )
		
class GetNetworkErrorsStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		psc_devices = self.make_query( 'sys_stat', self.get_os_devices( data[ "date_a" ], data[ "date_b" ], [ "RX-ERR", "RX-DRP", "RX-OVR", "TX-ERR", "TX-DRP", "TX-OVR" ] ), data["node_name"] )
		for device in psc_devices:
			if [ data["node_name"], device[0] ] in self.current_user_devices:
				queries = self.generate_query_os_stat( data[ "date_a" ], data[ "date_b" ], device[0], [ "RX-ERR", "RX-DRP", "RX-OVR", "TX-ERR", "TX-DRP", "TX-OVR" ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'RX-ERR RX-DRP RX-OVR TX-ERR TX-DRP TX-OVR (' + device[0] + '), packets', 'stackedColumn' ] )

		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )
	
class GetBlockHitDBHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""
		
		current_user_dbs = []
		for db in self.current_user_dbs:
			if data["node_name"] == db[0]:
				current_user_dbs.append( db[1] )
		
		queries = self.generate_query( current_user_dbs, data[ "date_a" ], data[ "date_b" ], 'blks_hit_per_sec' )
		data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), 'blks_hit_per_sec', 'line' ] )
		
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )
		
class GetBgwriterStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""
			
		queries = self.generate_query_common_stat( data[ "date_a" ], data[ "date_b" ], [ 'checkpoints_timed', 'checkpoints_req' ] )
		data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
			'checkpoints_timed, checkpoints_req', 'stackedColumn' ] )

		queries = self.generate_query_common_stat( data[ "date_a" ], data[ "date_b" ], [ 'checkpoint_write_time', 'checkpoint_sync_time' ], 'millisec_to_sec' )
		data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
			'checkpoint_write_time, checkpoint_sync_time; sec', 'stackedColumn' ] )
		
		queries = self.generate_query_common_stat( data[ "date_a" ], data[ "date_b" ], [ 'buffers_checkpoint', 'buffers_clean', 'buffers_backend', 'buffers_alloc' ], 'blocks_to_mb' )
		data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
			'buffers_checkpoint, buffers_clean, buffers_backend, buffers_alloc; MB', 'stackedArea' ] )
		
		queries = self.generate_query_common_stat( data[ "date_a" ], data[ "date_b" ], [ 'maxwritten_clean', 'buffers_backend_fsync' ] )
		data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
			'maxwritten_clean, buffers_backend_fsync', 'stackedColumn' ] )
		
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )
		
class GetBlockReadDBHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		current_user_dbs = []
		for db in self.current_user_dbs:
			if data["node_name"] == db[0]:
				current_user_dbs.append( db[1] )
				
		queries = self.generate_query( current_user_dbs, data[ "date_a" ], data[ "date_b" ], 'blks_read_per_sec' )
		data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), 'blks_read_per_sec', 'line' ] )	
		
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )
		
class GetTupWriteDBHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				queries = self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], ['tup_inserted_per_sec', 'tup_updated_per_sec', 'tup_deleted_per_sec' ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'tup_inserted_per_sec, tup_updated_per_sec, tup_deleted_per_sec (' + db[1] + ')', 'line' ] )
				
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetTupRetFetchDBHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				queries = self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], ['tup_returned_per_sec', 'tup_fetched_per_sec' ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'tup_returned_per_sec, tup_fetched_per_sec (' + db[1] + ')', 'line' ] )

		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )
		
class GetTxDBHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		current_user_dbs = []
		for db in self.current_user_dbs:
			if data["node_name"] == db[0]:
				current_user_dbs.append( db[1] )

		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				queries = self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], [ 'xact_commit_per_sec', 'xact_rollback_per_sec' ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
					'xact_commit_per_sec, xact_rollback_per_sec (' + db[1] + ')', 'stackedArea' ] )

		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )
		
class GetDeadlocksDBHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		current_user_dbs = []
		for db in self.current_user_dbs:
			if data["node_name"] == db[0]:
				current_user_dbs.append( db[1] )
			
		queries = self.generate_query( current_user_dbs, data[ "date_a" ], data[ "date_b" ], 'deadlocks' )
		data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), 'deadlocks', 'line' ] )		
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetAutovacStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		for db in self.current_user_dbs:
			if data["node_name"] == db[0]:
				queries = self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], ['autovacuum_workers_total','autovacuum_workers_wraparound'] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), \
					self.make_query( 'sys_stat', queries[1], data["node_name"] ), 'autovacuum_workers_total, autovacuum_workers_wraparound', 'stackedColumn' ] )
			
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )
		
class GetConnsStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				queries = self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], ['idle in transaction','idle','active','waiting_conns'] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), \
				'idle in transaction, idle, active, waiting_conns (' + db[1] + ')', 'stackedArea' ] )
			
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

	
class GetLocksStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""

		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				queries = self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], \
					[ 'AccessShareLock', 'RowExclusiveLock', 'ExclusiveLock', 'ShareRowExclusiveLock', 'RowShareLock', 'ShareLock', \
					'AccessExclusiveLock', 'RowShareUpdateExclusiveLock' ] )
				data_graph.append( [ self.make_query( 'sys_stat', queries[0], data["node_name"] ), self.make_query( 'sys_stat', queries[1], data["node_name"] ), 'All locks (' + db[1] + ')', 'stackedArea' ] )
		
		return self.make_line_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetWriteStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleTblStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'n_tup_ins_per_sec' ), data["node_name"] ), 'n_tup_ins_per_sec (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'n_tup_upd_per_sec' ), data["node_name"] ), 'n_tup_upd_per_sec (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'n_tup_hot_upd_per_sec' ), data["node_name"] ), 'n_tup_hot_upd_per_sec (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'n_tup_del_sec' ), data["node_name"] ), 'n_tup_del_per_sec (' + db[1] + ')' ] )

		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetTupStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleTblStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []
		
		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:	
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'tup_fetch_sum' ), data["node_name"] ), 'tup_fetch_sum (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'idx_tup_fetch_per_sec' ), data["node_name"] ), 'idx_tup_fetch_per_sec (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'seq_tup_read_per_sec' ), data["node_name"] ), 'seq_tup_read_per_sec (' + db[1] + ')' ] )			  

		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] ) 
	
class GetIdxStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleTblStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []
		
		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:	
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'by_idx_scan_per_sec' ), data["node_name"] ), 'idx_scan_per_sec (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'by_idx_tup_read_per_sec' ), data["node_name"] ), 'idx_tup_read_per_sec (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'by_idx_tup_fetch_per_sec' ), data["node_name"] ), 'idx_tup_fetch_per_sec (' + db[1] + ')' ] )			  

		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetIndexStatHandler(BaseAsyncHandlerNoParam,Chart,QueryMakerSimpleTblStat):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body)
		data_graph = []

		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'reads / fetched' ), data["node_name"] ), 'read / fetched (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'reads / scans' ), data["node_name"] ), 'read / scans (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.generate_query( db[1], data[ "date_a" ], data[ "date_b" ], 'fetched / scans' ), data["node_name"] ), 'fetched / scans (' + db[1] + ')' ] )

		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetQueryDurationsHandler(BaseAsyncHandlerNoParam,Chart):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body)
		data_graph = []

		query = """
			select row_number() OVER(PARTITION BY T.dt_rounded ORDER BY T.dt_rounded ) AS graph_block, T.* 
			from 
			(
				select 
					psc_round_minutes( q.dt """ + timezone_correct_time_backward +""" , 10 )::timestamp without time zone as dt_rounded, 
					(round(q.duration::numeric / 1000, 2)) as duration_sec, 
					q.id, q.query, q.plan, 
					(round(q.io_read_time::numeric / 1000, 2)) as io_read_time_sec, 
					( select pg_size_pretty((( q.read_v )*8192)::bigint) ) as total_read_blks_size_detail
					FROM psc_queries_and_plans q
					inner join psc_dbs d on q.db_id = d.id
					where dt >= '""" + data["date_a" ] + """'::timestamp """ + timezone_correct_time_forward + """ and dt < '""" + data["date_b" ] + """'::timestamp """ + timezone_correct_time_forward +""" and d.db_name = '%s'
					order by dt_rounded asc, duration asc
			) T order by T.dt_rounded asc, graph_block asc"""

			
		if self.check_auth() == False:
			return ""

		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				data_graph.append( [ self.make_query( 'sys_stat', query % (db[1]), data["node_name"] ), 'Query durations in sec (' + db[1] + ')' ] )
				
		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetQueryIODurationsHandler(BaseAsyncHandlerNoParam,Chart):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		query = """
		select row_number() OVER(PARTITION BY T.dt_rounded ORDER BY T.dt_rounded ) AS graph_block, T.* 
					from 
					(
						select 
							psc_round_minutes( q.dt """ + timezone_correct_time_backward +""" , 10 )::timestamp without time zone as dt_rounded, 
							(round(q.io_read_time::numeric / 1000, 2)) as io_read_time_sec, 
							q.id, q.query, q.plan, 
							( select pg_size_pretty((( q.read_v )*8192)::bigint) ) as total_read_blks_size_detail,
							(round(duration::numeric / 1000, 2)) as duration_sec
							FROM psc_queries_and_plans q
							inner join psc_dbs d on q.db_id = d.id
							where dt >= '""" + data["date_a" ] + """'::timestamp """ + timezone_correct_time_forward + """ and dt < '""" + data["date_b" ] + """'::timestamp """ + timezone_correct_time_forward +""" and d.db_name = '%s'
							order by dt_rounded asc, io_read_time asc
					) T order by T.dt_rounded asc, graph_block asc"""
		
		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:	
				data_graph.append( [ self.make_query( 'sys_stat', query % (db[1]), data["node_name"] ), 'I/O Timings read by queries (' + db[1] + ')' ] )
		
		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetQueryBlksHandler(BaseAsyncHandlerNoParam,Chart):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		query = """
		
		select row_number() OVER(PARTITION BY T.dt_rounded ORDER BY T.dt_rounded ) AS graph_block, T.* 
							from 
							(
								select 
									psc_round_minutes( q.dt """ + timezone_correct_time_backward +""" , 10 )::timestamp without time zone as dt_rounded, 
									(shared_hit_v + read_v + dirtied_v) as total_blks_size, 
									q.id, q.query, q.plan, 
									total_blks_size as total_blks_size_detail
									FROM psc_queries_and_plans q
									inner join psc_dbs d on q.db_id = d.id
									where dt >= '""" + data["date_a" ] + """'::timestamp """ + timezone_correct_time_forward + """ and dt < '""" + data["date_b" ] + """'::timestamp """ + timezone_correct_time_forward +""" and d.db_name = '%s'
									order by dt_rounded asc, total_blks_size asc
							) T order by T.dt_rounded asc, graph_block asc"""
		
		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				data_graph.append( [ self.make_query( 'sys_stat', query % (db[1]), data["node_name"] ), 'Blocks by queries (' + db[1] + ')' ] )
		
		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )
#=======================================================================================================
class StmStatQuery():
	def query(self, timezone_correct_time_backward, timezone_correct_time_forward, date_a, date_b, metric):
		return """
		select row_number() OVER(PARTITION BY T.dt_rounded ORDER BY T.dt_rounded ) AS graph_block, T.* 
							from 
							(
								select 
									( s.dt """ + timezone_correct_time_backward +""" )::timestamp without time zone as dt_rounded, 
									round(s.val, 3), 
									s.id, q.query_text as stm_query
									FROM psc_stm_stat s
									inner join psc_stm_queries q on q.id = s.query_id
									inner join psc_dbs d on d.id = s.db_id
									inner join psc_params p on p.id = s.param_id
									where p.param_name = '""" + metric + """' and dt >= '""" + date_a + """'::timestamp """ + timezone_correct_time_forward + """ and 
										dt < '""" + date_b + """'::timestamp """ + timezone_correct_time_forward +""" and d.db_name = '%s'
									order by dt_rounded asc, val asc
							) T order by T.dt_rounded asc, graph_block asc"""


class GetStmCallsByQueriesHandler(BaseAsyncHandlerNoParam,Chart,StmStatQuery):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		query = self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_calls')

		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				data_graph.append( [ self.make_query( 'sys_stat', query % (db[1]), data["node_name"] ), 'Calls by Queries (' + db[1] + ')' ] )
		
		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetStmTotalTimeByQueriesHandler(BaseAsyncHandlerNoParam,Chart,StmStatQuery):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		query = self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_total_time')

		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				data_graph.append( [ self.make_query( 'sys_stat', query % (db[1]), data["node_name"] ), 'Total time by queries (' + db[1] + ')' ] )
		
		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetStmRowsByQueriesHandler(BaseAsyncHandlerNoParam,Chart,StmStatQuery):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		query = self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_rows')

		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				data_graph.append( [ self.make_query( 'sys_stat', query % (db[1]), data["node_name"] ), 'Rows by queries (' + db[1] + ')' ] )
		
		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetStmSharedBlksByQueriesHandler(BaseAsyncHandlerNoParam,Chart,StmStatQuery):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				data_graph.append( [ self.make_query( 'sys_stat', self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_shared_blks_hit') % \
					(db[1]), data["node_name"] ), 'Shared blks hit by queries (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_shared_blks_read') % \
					(db[1]), data["node_name"] ), 'Shared blks read by queries (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_shared_blks_dirtied') % \
					(db[1]), data["node_name"] ), 'Shared blks dirtied by queries (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_shared_blks_written') % \
					(db[1]), data["node_name"] ), 'Shared blks written by queries (' + db[1] + ')' ] )

		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetStmLocalBlksByQueriesHandler(BaseAsyncHandlerNoParam,Chart,StmStatQuery):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				data_graph.append( [ self.make_query( 'sys_stat', self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_local_blks_hit') % \
					(db[1]), data["node_name"] ), 'Local blks hit by queries (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_local_blks_read') % \
					(db[1]), data["node_name"] ), 'Local blks read by queries (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_local_blks_dirtied') % \
					(db[1]), data["node_name"] ), 'Local blks dirtied by queries (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_local_blks_written') % \
					(db[1]), data["node_name"] ), 'Local blks written by queries (' + db[1] + ')' ] )	
		
		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetStmTempBlksReadWriteTimeByQueriesHandler(BaseAsyncHandlerNoParam,Chart,StmStatQuery):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				data_graph.append( [ self.make_query( 'sys_stat', self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_temp_blks_read') % \
					(db[1]), data["node_name"] ), 'Temp blks read by queries (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_temp_blks_written') % \
					(db[1]), data["node_name"] ), 'Temp blks written by queries (' + db[1] + ')' ] )
		
		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

class GetStmBlkReadWriteTimeByQueriesHandler(BaseAsyncHandlerNoParam,Chart,StmStatQuery):
	def post_(self):
		data = tornado.escape.json_decode(self.request.body) 
		data_graph = []

		if self.check_auth() == False:
			return ""
		
		for db in self.current_user_dbs:
			if db[0] == data["node_name"]:
				data_graph.append( [ self.make_query( 'sys_stat', self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_blk_read_time') % \
					(db[1]), data["node_name"] ), 'Blk read time by queries (' + db[1] + ')' ] )
				data_graph.append( [ self.make_query( 'sys_stat', self.query(timezone_correct_time_backward, timezone_correct_time_forward, data["date_a" ], data["date_b" ], 'stm_blk_write_time') % \
					(db[1]), data["node_name"] ), 'Blk write time by queries (' + db[1] + ')' ] )
		
		return self.make_stacked_report( data_graph, [data[ "date_a" ], data[ "date_b" ]] )

#=======================================================================================================
class GetActivityHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getActivity', 3 )

class GetLocksHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getLocks', 10 )

class GetLocksPairsHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getLocksPairs', 10 )

class GetStatementsHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getStatements', 10 )

class GetLongQueriesHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getLongQueries', 10 )
		
class GetTblSizesHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getTblSizes' )

class GetIdxSeqTupFetchHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getIdxSeqTupFetch' )
		
class GetUnusedIdxsHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getUnusedIdxs' )
		
class GetIndexBloatHandler(BaseAsyncHandlerNoParam):
	def post_(self):	
		return self.proxy_http_post( 'getIndexBloat' )

class GetTableBloatHandler(BaseAsyncHandlerNoParam):
	def post_(self):		
		return self.proxy_http_post( 'getTableBloat' )

class GetPGConfigHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getPGConfig', 3 )

#=======================================================================================================
class GetLogHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getLog' )

class GetListLogFilesHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getListLogFiles', 3 )

class DownloadLogFileHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		params = tornado.escape.json_decode(self.request.body)
		file_name = self.proxy_http_post( 'downloadLogFile' )
		if file_name == 'No enougth rights':
			return file_name
		log_file = "http://" + self.get_pg_stat_monitor_host(params[ "node_name" ]) + self.proxy_http_post( 'downloadLogFile' )
		new_name = os.path.basename(log_file)
		new_name = "f_" + new_name
		urllib.request.urlretrieve( log_file, current_dir + 'download/' + new_name )
		return '/download/' + new_name
#=======================================================================================================

def make_activity_report( date_a, date_b, dates, date_s, psc_conns, locks, pg_vers ):
	#dates, params[ "date_s" ], psc_conns, locks
	html_report = ""
	
	html_report = html_report + """<div style="text-align: center;">""";
	for date in dates:
		if str( date[1] ) == str( date_s ):
			html_report = html_report + """<div class="date_link hvr-shutter-out-horizontal pg_stat_console_date_link_active" key_id=\"""" + str(date[0]) + """\">""" + str(date[1]) + """</div>"""
		else:
			html_report = html_report + """<div class="date_link hvr-shutter-out-horizontal pg_stat_console_date_link" key_id=\"""" + str(date[0]) + """\">""" + str(date[1]) + """</div>"""
	html_report = html_report + """</div>""";   
	
	if pg_vers == "9.6":
		html_report = html_report + make_html_report_with_head( psc_conns, [ "db_name", "app_name", "user_name", "state_name", "pid", "client_addr", "query_start", "age", "wait_event_type", "wait_event", "query" ], "Connections", ["query"] )
	else:
		html_report = html_report + make_html_report_with_head( psc_conns, [ "db_name", "app_name", "user_name", "state_name", "pid", "client_addr", "query_start", "age", "waiting", "query" ], "Connections", ["query"] )
	
	html_report = html_report + make_html_report_with_head( locks, [ "waiting_table", "waiting_query", "waiting_pid", "lock_mode", "lock_type", "other_table", "other_query", "other_pid", "db_name" ], "Locks", ["other_query","waiting_query"] )
		
	return html_report
	

class GetActivityHistoryHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		params = tornado.escape.json_decode(self.request.body) 

		dates = []
		psc_conns = []
		locks = []
		date_s = ""
		
		dates = self.make_query( 'sys_stat', """SELECT id, (dt """ + timezone_correct_time_backward +""")::text
			FROM psc_snapshots where dt >= '""" + params[ "date_a" ] + """'::timestamp """ + timezone_correct_time_forward + \
			""" and dt < '""" + params[ "date_b" ] + """'::timestamp """ + timezone_correct_time_forward +"""
			order by dt asc
			limit 1000""", params[ "node_name" ] )
	
		if 'date_s' in params:
			date_s = params[ "date_s" ]

			if self.get_pg_version() == "9.6":
				psc_conns = self.make_query( 'sys_stat', """SELECT db.db_name, an.app_name, usr.user_name, cs.state_name, cn.pid, cn.client_addr,
					cn.query_start """ + timezone_correct_time_backward +""", age(sn.dt,cn.query_start) as age, 
					wt."wait_type", wn."wait_name", cn.query
					  FROM psc_snapshots sn
					  inner join psc_conns cn on cn.sn_id = sn.id
					  inner join psc_dbs db on db.id = cn.db_id
					  inner join psc_users usr on usr.id = cn.user_id
					  inner join psc_app_names an on an.id = cn.app_name
					  inner join psc_conn_states cs on cs.id = cn.conn_state
					  inner join psc_wait_names wn on wn.id = cn."wait_event"
					  inner join psc_wait_types wt on wt.id = cn."wait_event_type"
					where sn.dt = '""" + params[ "date_s" ] + """'::timestamp with time zone """ + timezone_correct_time_forward + """""", params[ "node_name" ] )	
			else:
				psc_conns = self.make_query( 'sys_stat', """SELECT db.db_name, an.app_name, usr.user_name, cs.state_name, cn.pid, cn.client_addr,
					cn.query_start """ + timezone_correct_time_backward +""", age(sn.dt,cn.query_start) as age, 
					cn.waiting, cn.query
					  FROM psc_snapshots sn
					  inner join psc_conns cn on cn.sn_id = sn.id
					  inner join psc_dbs db on db.id = cn.db_id
					  inner join psc_users usr on usr.id = cn.user_id
					  inner join psc_app_names an on an.id = cn.app_name
					  inner join psc_conn_states cs on cs.id = cn.conn_state
					where sn.dt = '""" + params[ "date_s" ] + """'::timestamp with time zone """ + timezone_correct_time_forward + """""", params[ "node_name" ] )
					
			locks = self.make_query( 'sys_stat', """select 
					tbls_w.tbl_name as waiting_table,
					l.waiting_query, 
					l.waiting_pid, 
					lm.lock_mode as lock_mode, 
					lt.lock_type as lock_type, 
					tbls_a.tbl_name as other_table,
					l.other_query, 
					l.other_pid,
					d.db_name
					FROM psc_snapshots sn
					inner join psc_locks l on l.sn_id = sn.id
					inner join psc_lock_modes lm on l.waiting_mode_id = lm.id 
					inner join psc_lock_types lt on l.waiting_locktype_id = lt.id
					inner join psc_tbls tbls_w on l.waiting_table_id = tbls_w.id
					inner join psc_tbls tbls_a on l.other_table_id = tbls_a.id
					inner join psc_dbs d on l.waiting_db_id = d.id
					where sn.dt = '""" + params[ "date_s" ] + """'::timestamp with time zone """ + timezone_correct_time_forward + """""", params[ "node_name" ] )

		return make_activity_report( params[ "date_a" ], params[ "date_b" ], dates, date_s, psc_conns, locks, self.get_pg_version() )

class GetActivityHistoryExtHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		params = tornado.escape.json_decode(self.request.body) 
		html_report = ""
		
		if self.get_pg_version() == "9.6":
				html_report = make_html_report_with_head( self.make_query( 'sys_stat', """select
					(sn.dt """ + timezone_correct_time_backward +""")::text,
					sum(case when wait_event_type is not null and cs.state_name = 'active' then 1 else 0 end) as active_waiting_count,
					sum(case when wait_event_type is null and cs.state_name = 'active' then 1 else 0 end) as active_count,
					sum(case when cs.state_name = 'idle' then 1 else 0 end) as idle_count,
					sum(case when cs.state_name = 'idle in transaction' then 1 else 0 end) as idle_in_tx_count,
					(select count(1) from psc_locks l where l.sn_id = sn.id ) as locks_count,
					sum(1) as total_conns,
					( '<div style="float:left;" link_val="' || sn.id::text || '" class="load_snapshot pg_stat_console_fonts pg_stat_console_button">Show snaphot</div>' ) as sn_id	 
					FROM psc_snapshots sn 
					inner join psc_conns cn on cn.sn_id = sn.id
					inner join psc_conn_states cs on cs.id = cn.conn_state  
					where sn.dt >= '""" + params[ "date_a" ] + """'::timestamp """ + timezone_correct_time_forward +""" and sn.dt < '""" + params[ "date_b" ] + """'::timestamp """ + timezone_correct_time_forward +"""
					group by sn.id, sn.dt
					order by dt asc
					limit 1000""", params[ "node_name" ] ), [ "datetime", "active_waiting_count", "active_count", "idle_count", "idle_in_tx_count", "locks_count", "total_conns", "show" ], "Snapthots", ["datetime","show"] )
		else:
				html_report = make_html_report_with_head( self.make_query( 'sys_stat', """select
					(sn.dt """ + timezone_correct_time_backward +""")::text,
					sum(case when waiting = true and cs.state_name = 'active' then 1 else 0 end) as active_waiting_count,
					sum(case when waiting = false and cs.state_name = 'active' then 1 else 0 end) as active_count,
					sum(case when cs.state_name = 'idle' then 1 else 0 end) as idle_count,
					sum(case when cs.state_name = 'idle in transaction' then 1 else 0 end) as idle_in_tx_count,
					(select count(1) from psc_locks l where l.sn_id = sn.id ) as locks_count,
					sum(1) as total_conns,
					( '<div style="float:left;" link_val="' || sn.id::text || '" class="load_snapshot pg_stat_console_fonts pg_stat_console_button">Show snaphot</div>' ) as sn_id	 
					FROM psc_snapshots sn 
					inner join psc_conns cn on cn.sn_id = sn.id
					inner join psc_conn_states cs on cs.id = cn.conn_state  
					where sn.dt >= '""" + params[ "date_a" ] + """'::timestamp """ + timezone_correct_time_forward +""" and sn.dt < '""" + params[ "date_b" ] + """'::timestamp """ + timezone_correct_time_forward +"""
					group by sn.id, sn.dt
					order by dt asc
					limit 1000""", params[ "node_name" ] ), [ "datetime", "active_waiting_count", "active_count", "idle_count", "idle_in_tx_count", "locks_count", "total_conns", "show" ], "Snapthots", ["datetime","show"] )
		
		return html_report

class GetOldConnsHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getOldConns', 3 )
		
class GetHistoryBySnIdHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		params = tornado.escape.json_decode(self.request.body) 
		html_report = ""
		
		if self.get_pg_version() == "9.6":
			html_report = make_html_report_with_head( self.make_query( 'sys_stat', """SELECT db.db_name, an.app_name, usr.user_name, cs.state_name, cn.pid, cn.client_addr,
					cn.query_start """ + timezone_correct_time_backward +""", age(sn.dt,cn.query_start) as age, 
					wt."wait_type", wn."wait_name", cn.query
					  FROM psc_snapshots sn
					  inner join psc_conns cn on cn.sn_id = sn.id
					  inner join psc_dbs db on db.id = cn.db_id
					  inner join psc_users usr on usr.id = cn.user_id
					  inner join psc_app_names an on an.id = cn.app_name
					  inner join psc_conn_states cs on cs.id = cn.conn_state
					  inner join psc_wait_names wn on wn.id = cn."wait_event"
					  inner join psc_wait_types wt on wt.id = cn."wait_event_type"
					where sn_id = """ + params[ "sn_id" ], params[ "node_name" ] ),  [ "db_name", "app_name", "user_name", "state_name", "pid", "client_addr", "query_start", "age", "wait_event_type", "wait_event", "query" ], "Connections", ["query"] )
		else:
			html_report = make_html_report_with_head( self.make_query( 'sys_stat', """SELECT db.db_name, an.app_name, usr.user_name, cs.state_name, cn.pid, cn.client_addr,
					cn.query_start """ + timezone_correct_time_backward +""", age(sn.dt,cn.query_start) as age, 
					cn.waiting, cn.query
					  FROM psc_snapshots sn
					  inner join psc_conns cn on cn.sn_id = sn.id
					  inner join psc_dbs db on db.id = cn.db_id
					  inner join psc_users usr on usr.id = cn.user_id
					  inner join psc_app_names an on an.id = cn.app_name
					  inner join psc_conn_states cs on cs.id = cn.conn_state
					where sn_id = """ + params[ "sn_id" ], params[ "node_name" ] ),  [ "db_name", "app_name", "user_name", "state_name", "pid", "client_addr", "query_start", "age", "waiting", "query" ], "Connections", ["query"] )
		
		html_report = html_report + make_html_report_with_head( self.make_query( 'sys_stat', """select 	
					tbls_w.tbl_name as waiting_table,
					l.waiting_query, 
					l.waiting_pid, 
					lm.lock_mode as lock_mode, 
					lt.lock_type as lock_type, 
					tbls_a.tbl_name as other_table,
					l.other_query, 
					l.other_pid,
					d.db_name
					FROM psc_snapshots sn
					inner join psc_locks l on l.sn_id = sn.id
					inner join psc_lock_modes lm on l.waiting_mode_id = lm.id 
					inner join psc_lock_types lt on l.waiting_locktype_id = lt.id
					inner join psc_tbls tbls_w on l.waiting_table_id = tbls_w.id
					inner join psc_tbls tbls_a on l.other_table_id = tbls_a.id
					inner join psc_dbs d on l.waiting_db_id = d.id
			where sn.id = """ + params[ "sn_id" ], params[ "node_name" ] ), [ "waiting_table", "waiting_query", "waiting_pid", "lock_mode", "lock_type", "other_table", "other_query", "other_pid", "db_name" ], "Locks", ["other_query","waiting_query"] )

		return html_report

class GetConnManagementHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getConnManagement' )
			  
class GetServerProcessesHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getServerProcesses' )
		
class GetIOServerProcessesHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'getIOServerProcesses' )
		
class StopQueryHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.proxy_http_post( 'stopQuery' )

class GetPgStatConsoleStatusHandler(BaseAsyncHandlerNoParam):
	def tail(self, file_name, n, offset=0):
		encoding = locale.getdefaultlocale()[1]
		cmd = subprocess.Popen("tail -n " + str(n) + str(offset) + " " + file_name,shell=True,stdout=subprocess.PIPE)
		lines = []
		line_num = 0
		for line in cmd.stdout:	
			lines.append( [ line_num, line.decode(encoding) ] )
			line_num = line_num + 1
		return lines
		
	def check_runned_process(self, proc_name):
		encoding = locale.getdefaultlocale()[1]
		cmd = subprocess.Popen("ps -eaf | grep " + proc_name,shell=True,stdout=subprocess.PIPE)
		for line in cmd.stdout:  
			line_str = str( line.decode(encoding) )
			if line_str.find("python3") > -1 and line_str.find(proc_name) > -1:
				return True
		return False

	def check_stat_data_db(self, db_name, node_name):
		result = self.make_query( "sys_stat", """select 
			( select exists(
				select T.db_name, T.dt from (
					select db_name, dt 
					from psc_dbs_stat s
					inner join psc_dbs d on s.db_id = d.id
					where db_name = '""" + db_name + """' and dt > clock_timestamp() - interval '30 minutes'
					limit 1
				) T
			) )
			and
			( select exists(
				select T.db_name, T.dt from (
					select db_name, dt 
					from psc_tbls_stat s 
					inner join psc_dbs d on s.db_id = d.id
					where db_name = '""" + db_name + """' and dt > clock_timestamp() - interval '30 minutes'
					limit 1
				) T
			) ) as result""", node_name )
							
		res = None
		for row in result:
			res = row['result']
		return res

	def check_stat_data_os(self, node_name):
		result = self.make_query( "sys_stat", """select 
			( select exists(
					select id
					from psc_os_stat os
					where dt > clock_timestamp() - interval '30 minutes'
					limit 1
			) ) as result""", node_name )
							
		res = None
		for row in result:
			res = row['result']
		return res

	def check_stat_data_sn(self, node_name):
		result = self.make_query( "sys_stat", """select 
			( 
				select exists( select 1 from ( 
					select dt from psc_snapshots 
				) T where dt > clock_timestamp() - interval '30 minutes' ) 
			) as result""", node_name )

		res = None
		for row in result:
			res = row['result']
		return res 

	def check_log_data(self, db_name, node_name ):
		result = self.make_query( "sys_stat", """
			select exists(
				select dt 
				from psc_queries_and_plans p
				inner join psc_dbs d on p.db_id = d.id
				where db_name = '""" + db_name + """' and dt > clock_timestamp() - interval '1 day'
				limit 1
			) as result""", node_name )
						
		res = None
		for row in result:
			res = row['result']
		return res
		
	def post_(self):
		if self.check_auth() == False:
			return "false"
		result = False

		data = tornado.escape.json_decode(self.request.body) 
		result = True

		for db in self.current_user_dbs:
			if data["node_name"] == db[0]:
				result = result and ( self.check_stat_data_db( db[1], data["node_name"] ) )
		
		self.set_header('Content-Type', 'application/json')
		return json.dumps(result, ensure_ascii=False).encode('utf8')

class GetConsoleStatusReportHandler(GetPgStatConsoleStatusHandler):
	def log_lines(self, app_name, limit_lines=100):
		log_lines_str = ""
		log_lines_list = self.tail( current_dir + 'log/' + app_name + '.log' , limit_lines )
		log_lines_list = sorted(log_lines_list, key=itemgetter(0), reverse=True)
		for line in log_lines_list:
			log_lines_str = log_lines_str + line[1] + "<br></br>" 
		return log_lines_str

	def post_(self):
		if self.check_auth() == False:
			return "false"
		
		html_report = ""
		databases = []
		data = tornado.escape.json_decode(self.request.body) 

		for db in self.current_user_dbs:
			if data["node_name"] == db[0]:
				db_stat_status = self.check_stat_data_db( db[1], data["node_name"] )
				databases.append( [ db[1], "yes" if db_stat_status else """<div class="pg_stat_console_alert_font">no</div>""" ] )

		if len( databases ) > 0:
			html_report = html_report + make_html_report_with_head( databases, [ "DB name", "Stat data collected" ], "Database status" )

		common_stat = []
		if len( databases ) > 0:
			common_stat.append( [ 'pg_stat_activity snapshots', "yes" if self.check_stat_data_sn(data["node_name"]) else """no""" ] )
		
		common_stat.append( [ 'OS stat', "yes" if self.check_stat_data_os(data["node_name"]) else """no""" ] )
		
		html_report = html_report + make_html_report_with_head( common_stat, [ "Data source", "Collected" ], "Common status" )
		
		if self.get_current_user_rights() == 'admin':
		
			users_stat = self.make_query( "sys_stat", """
				SELECT substring(user_hash from 1 for 8), dt::timestamp(0) without time zone, user_name, user_ip, user_agent
				FROM public.psc_user_hashes
				order by dt desc
				limit 100""", data["node_name"] )
							
			html_report = html_report + make_html_report_with_head( users_stat, [ "Hash", "Created", "User name", "User IP", "User agent" ], "Users info", [ "User name", "User IP" ] )
			
			html_report = """<div id="sub_space" class="pg_stat_console_fonts_on_white_na pg_stat_console_log_caption">""" + \
				html_report + """<h2 style ="text-align: center;font-size: 16px;" class="scrollable_obj">pg_stat_console logs</h2>"""
			html_report = html_report + self.log_lines(application_name)

		html_report = html_report + """</div>"""
		return html_report

class GetPgStatConsoleNodeInfoHandler(GetPgStatConsoleStatusHandler):
	def post_(self):
		if self.check_auth() == False:
			return "false"
		
		data = tornado.escape.json_decode(self.request.body) 
		
		result = self.make_query( "sys_stat", """select * from public.psc_get_node_info(
			(SELECT 'n' || id FROM public.psc_nodes where node_name = '""" + data["node_name"] + """'), '1 hour')""" )

		res = []
		for row in result:
			res.append( row[0] )
			
		if self.proxy_http_post( 'getUptime' ) != "pg_stat_monitor not allowed":
			res.append( 'pg_stat_monitor' )

		self.set_header('Content-Type', 'application/json')
		return json.dumps(res, ensure_ascii=False).encode('utf8')

class GetMaintenanceStatusHandler(BaseAsyncHandlerNoParam):   
	def post_(self):
		return self.proxy_http_post( 'getMaintenanceStatus' )

class GetMaintenanceTasksHandler(BaseAsyncHandlerNoParam):   
	def post_(self):
		return self.proxy_http_post( 'getMaintenanceTasks' )

class GetUserTypeHandler(BaseAsyncHandlerNoParam):   
	def post_(self):
		if self.check_auth() == False:
			return "false"

		params = tornado.escape.json_decode(self.request.body)	  
		for user in users_list:
			if user[0] == params["user_name"]:
				return user[2]
		return 'none'
		
class ShowUserConfigHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		if self.check_auth() == False:
			return "false"
		user_config = ""

		nodes = self.make_query( 'sys_stat', """SELECT id, node_name FROM public.psc_nodes""" )
		unv = self.get_current_user_nodes_visibility()

		for node in nodes:
			if len( unv ) > 0 and node['node_name'] not in unv:
				continue
			databases = []
			psc_devices = []
			result = self.make_query( 'sys_stat', """SELECT device_name, device_type FROM psc_devices;""", node['node_name'] )
			for row in result:
				psc_devices.append( [ row['device_name'], row['device_type'], '<input class="conf_param" type="checkbox" param_name="' + row['device_name'] + '" node_name="' +  node['node_name'] + '" param_type="device_in_report" value="a1">Yes</input>' ] )	

			result = self.make_query( 'sys_stat', """SELECT db_name FROM psc_dbs where db_name not in ('postgres', 'template0', 'template1');""", node['node_name'] )
			for row in result:
				databases.append( [ row['db_name'],'<input class="conf_param" type="checkbox" param_name="' + row['db_name'] + '" node_name="' +  node['node_name'] + '" param_type="db_in_report" value="a1">Yes</input>' ] )	

			user_config += """
				<div style="width: 100%;text-align: center;margin-top:15px;">
					<div style="height:50px;display: inline-block;">
						<div class="pg_stat_console_fonts_on_white " style="float:left;">
							<h2 style="text-align: center;font-size: 20px;">""" + node['node_name'] + """</h2>
						</div>
						<div style="margin-left:20px;float:left;margin-top:15px;" class="select_all pg_stat_console_fonts pg_stat_console_button" node_name=\"""" + node['node_name'] + """\">Select all</div>
						<div style="margin-left:20px;float:left;margin-top:15px;" class="deselect_all pg_stat_console_fonts pg_stat_console_button" node_name=\"""" + node['node_name'] + """\">Deselect all</div>
					</div>
				</div>"""

			if len(psc_devices) > 0:
				user_config += make_html_report_with_head( psc_devices,   [ "Device name", "Device type", "In report" ], "Devices in report (" + node['node_name'] + ")" ) 
			if len(databases) > 0:	
				user_config += make_html_report_with_head( databases, [ "DB name", "In report" ], "Databases in report (" + node['node_name'] + ")" )

		return user_config
	
class GetDashboardConfigHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		if self.check_auth() == False:
			return "false"

		result = []
		for user_dashboard in users_dashboards:
			if user_dashboard[0] == self.get_current_user_name():
				result = user_dashboard[1]

		self.set_header('Content-Type', 'application/json')
		return json.dumps(result, ensure_ascii=False).encode('utf8') 

application = tornado.web.Application([
			(r"/(.*\.html)", PgStatConsoleStaticFileHandler,{"path": current_dir }),
			(r"/(.*\.png)", PgStatConsoleStaticFileHandler,{"path": current_dir }),
			(r"/(.*\.jpg)", PgStatConsoleStaticFileHandler,{"path": current_dir }),
			(r"/(.*\.gif)", PgStatConsoleStaticFileHandler,{"path": current_dir }),
			(r"/(.*\.ico)", PgStatConsoleStaticFileHandler,{"path": current_dir }),
			(r"/(.*\.js)", PgStatConsoleStaticFileHandler,{"path": current_dir }),
			(r"/(.*\.css)", PgStatConsoleStaticFileHandler,{"path": current_dir }),  
			(r"/(.*\.ttf)", PgStatConsoleStaticFileHandler,{"path": current_dir }), 
			(r"/(.*\.gz)", PgStatConsoleStaticFileHandler,{"path": current_dir }),  
			('/main', MainHandler),
			('/', MainHandler),
			('/login', LoginHandler),
			('/check_user_hash', UserHashHandler),
			('/getCustomParam', GetCustomParamHandler),
			
			('/getDashboardConfig', GetDashboardConfigHandler),

			('/getOSParamValue', GetOSParamValueHandler),

			('/getCPUStat', GetCPUStatHandler),
			('/getMemUsageStat', GetMemUsageStatHandler),
			('/getDiskUtilStat', GetDiskUtilStatHandler),
			('/getDiskUsageStat', GetDiskUsageStatHandler),
			('/getWRQMRRQMStat', GetWRQMRRQMStatHandler),
			('/getWRStat', GetWRStatHandler),	
			('/getRSecWSecStat', GetRSecWSecStatHandler),
			('/getAVGRQStat', GetAVGRQStatHandler),	
			('/getAVGQUStat', GetAVGQUStatHandler),
			('/getAWaitStat', GetAWaitStatHandler),
			('/getNetworkTrafficStat', GetNetworkTrafficStatHandler),
			('/getNetworkPacketsStat', GetNetworkPacketsStatHandler),
			('/getNetworkErrorsStat', GetNetworkErrorsStatHandler),

			('/getReadStat', GetReadStatHandler),
			('/getWriteStat', GetWriteStatHandler),
			('/getTupStat', GetTupStatHandler),
			('/getIdxStat', GetIdxStatHandler),
			('/getIndexStat', GetIndexStatHandler),
			('/getQueryDurations', GetQueryDurationsHandler),
			('/getQueryIODurations', GetQueryIODurationsHandler),
			('/getQueryBlks', GetQueryBlksHandler),

			('/getBgwriterStat', GetBgwriterStatHandler ),
			('/getBlockHitDB', GetBlockHitDBHandler),
			('/getBlockReadDB', GetBlockReadDBHandler),
			('/getTupWriteDB', GetTupWriteDBHandler),
			('/getTupRetFetchDB', GetTupRetFetchDBHandler),
			('/getTxDB', GetTxDBHandler),
			('/getDeadlocksDB', GetDeadlocksDBHandler),

			('/getAutovacStat', GetAutovacStatHandler),
			('/getConnsStat', GetConnsStatHandler),
			('/getLocksStat', GetLocksStatHandler),

			('/getActivityHistory', GetActivityHistoryHandler),
			('/getActivityHistoryExt',GetActivityHistoryExtHandler),
			('/getHistoryBySnId', GetHistoryBySnIdHandler ),

			('/getRefreshInterval', GetRefreshIntervalHandler),

			('/getPgStatConsoleNodeInfo', GetPgStatConsoleNodeInfoHandler),
			('/getConsoleStatusReport', GetConsoleStatusReportHandler),
			('/getUserType', GetUserTypeHandler),
			('/getPgStatConsoleStatus', GetPgStatConsoleStatusHandler),
			
			('/showUserConfig', ShowUserConfigHandler),
			
			('/getStmCallsByQueries', GetStmCallsByQueriesHandler),
			('/getStmTotalTimeByQueries', GetStmTotalTimeByQueriesHandler),
			('/getStmRowsByQueries', GetStmRowsByQueriesHandler),
			
			('/getStmSharedBlksByQueries', GetStmSharedBlksByQueriesHandler),
			('/getStmLocalBlksByQueries', GetStmLocalBlksByQueriesHandler),
			('/getStmTempBlksReadWriteTimeByQueries', GetStmTempBlksReadWriteTimeByQueriesHandler),
			('/getStmBlkReadWriteTimeByQueries', GetStmBlkReadWriteTimeByQueriesHandler),

			#===================================================================
			# proxy methods for pg_stat_monitor
			('/getMaintenanceTasks', GetMaintenanceTasksHandler),
			('/getMaintenanceStatus', GetMaintenanceStatusHandler),
			('/getUptime', GetUptimeHandler),
			('/getConnManagement', GetConnManagementHandler),
			('/stopQuery', StopQueryHandler),
			('/getServerProcesses', GetServerProcessesHandler),
			('/getIOServerProcesses', GetIOServerProcessesHandler),
			('/getOldConns', GetOldConnsHandler),

			('/getLog', GetLogHandler),
			('/getListLogFiles', GetListLogFilesHandler),
			('/downloadLogFile', DownloadLogFileHandler),

			('/getActivity', GetActivityHandler),
			('/getLocks', GetLocksHandler),
			('/getLocksPairs', GetLocksPairsHandler),
			('/getStatements', GetStatementsHandler),
			('/getLongQueries', GetLongQueriesHandler),
			('/getTblSizes', GetTblSizesHandler),
			('/getUnusedIdxs', GetUnusedIdxsHandler),
			('/getIndexBloat', GetIndexBloatHandler),
			('/getIdxSeqTupFetch', GetIdxSeqTupFetchHandler),
			('/getTableBloat', GetTableBloatHandler),
			('/getPGConfig', GetPGConfigHandler)
			#===================================================================
	])

application.listen( int( port ) )
logger.log( "Application is ready to work! Port " + str( port ), "Info" )
IOLoop.instance().start()