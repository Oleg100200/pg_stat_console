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
import sys
import resource
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
#=======================================================================================================
current_dir = os.path.dirname(os.path.realpath(__file__)) + '/'
prepare_dirs(current_dir)
#=======================================================================================================
config = configparser.RawConfigParser()
config.optionxform = lambda option: option
config.read( current_dir + 'conf/pg_stat_monitor.conf')
#=======================================================================================================
limit_memory( 1024 * 1000 * int( read_conf_param_value( config['main']['application_max_mem'] ) ) )
#=======================================================================================================
EXECUTOR = ThreadPoolExecutor(max_workers=int( read_conf_param_value( config['main']['max_workers'] ) ))
#=======================================================================================================
pool_size_conf = int( read_conf_param_value( config['main']['db_pool_size'] ) )
timezone_correct_time_backward = read_conf_param_value( config['main']['timezone_correct_time_backward'] )
timezone_correct_time_forward = read_conf_param_value( config['main']['timezone_correct_time_forward'] ) 

allow_host = read_conf_param_value( config['main']['allow_host'] )
allow_host_list = []
for v in allow_host.split(','):
	allow_host_list.append( v.strip() )
#=======================================================================================================
dbs_list = []
for db in config['databases']: 
	dbs_list.append( db )

check_base = dbs_list[0]

db_pools = []
for db in config['databases']: 
	db_pools.append( [ db, create_engine(read_conf_param_value( config['databases'][db] ) + '?application_name=' + read_conf_param_value( config['main']['application_name'] ), \
		pool_size=pool_size_conf, max_overflow=0, poolclass=QueuePool, pool_recycle=int(read_conf_param_value( config['main']['db_pool_recycle'] ))) ] )

session_factorys = []
for pool in db_pools:
	session_factorys.append( [ pool[0], sessionmaker(bind=pool[1],autocommit=False) ] )

scoped_sessions = []
for session_factory in session_factorys:
	scoped_sessions.append( [ session_factory[0], scoped_session(session_factory[1]) ] )
#=======================================================================================================
application_name = read_conf_param_value( config['main']['application_name'] ) 
time_zone = read_conf_param_value( config['main']['time_zone'] )
enable_exception_catching = read_conf_param_value( config['main']['enable_exception_catching'], True )
hide_password_in_queries = read_conf_param_value( config['main']['hide_password_in_queries'], True )
hide_host_in_queries = read_conf_param_value( config['main']['hide_host_in_queries'], True )
port = int( read_conf_param_value( config['main']['port'] ) )
pg_log_dir = read_conf_param_value( config['main']['pg_log_dir'] )
pg_log_file_extension = read_conf_param_value( config['main']['pg_log_file_extension'] )
pg_log_line_max_len = read_conf_param_value( config['main']['pg_log_line_max_len'] )
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
				
	def make_query( self, db_name, query_text ):
		global scoped_sessions
		list = []

		logger.log( "call make_query(" + self.__class__.__name__  + "), db_name = " + db_name, "Info" )
		self.session = next(scoped_session[1] for scoped_session in scoped_sessions if scoped_session[0]==db_name)

		with self.closing( self.session ) as session:
			session.execute( """set application_name = '""" + application_name + """'""" )
			session.execute( """SET timezone = '""" + time_zone + """';""" )
			backend_pid = session.execute( """select pg_backend_pid() as pid""" )
			for row in backend_pid:
				self.db_pid = row['pid']

			logger.log( "call make_query(" + self.__class__.__name__  + "), db_name = " + db_name + \
				", db_pid = " + str( self.db_pid ), "Info" )
			list = session.execute( query_text )
		return list

	def on_connection_close(self):
		if self.db_pid is not None:
			logger.log( "stop_query = " + str( stop_query( self.db_pid ) ), "Info" )
			
	def get_pg_version(self, db):
		pg_version_res = self.make_query( db, """select case 
			when position( '9.6.' in version() ) > 0 then '9.6' 
			when position( '9.5.' in version() ) > 0 then '9.5' 
			when position( '9.4.' in version() ) > 0 then '9.4' 
			when position( '9.3.' in version() ) > 0 then '9.3' 
			when position( '9.2.' in version() ) > 0 then '9.2' 
			when position( '9.1.' in version() ) > 0 then '9.1'
			else 'unknown'
			end""" )
		
		pg_version = ""
		for v in pg_version_res:
			pg_version = v[0]
		return pg_version

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

		incoming_host = self.request.headers.get('X-Real-Ip', self.request.remote_ip)
		if incoming_host in allow_host_list:
			EXECUTOR.submit(
				partial(self.get_)
			).add_done_callback(
				lambda future: tornado.ioloop.IOLoop.instance().add_callback(
					partial(callback, future)))
		else:
			logger.log( "Host " + incoming_host + " not alowed!" , "Error" )
			self.clear()
			self.set_status(400)
			self.finish( "Host " + incoming_host + " not alowed!" )
			
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

		incoming_host = self.request.headers.get('X-Real-Ip', self.request.remote_ip)
		if incoming_host in allow_host_list:
			EXECUTOR.submit(
				partial(self.post_)
			).add_done_callback(
				lambda future: tornado.ioloop.IOLoop.instance().add_callback(
					partial(callback, future)))
		else:
			logger.log( "Host " + incoming_host + " not alowed!" , "Error" )
			self.clear()
			self.set_status(400)
			self.finish( "Host " + incoming_host + " not alowed!" )

class PgStatConsoleStaticFileHandler(tornado.web.StaticFileHandler):
	def set_extra_headers(self, path):
		self.set_header('Cache-Control', 'store, cache, must-revalidate, max-age=0')	
#=======================================================================================================
class GetUptimeHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		result = self.make_query( check_base, """SELECT date_trunc('second', current_timestamp - pg_postmaster_start_time())::text as uptime""" )
		res = ""
		for row in result:
			res = row['uptime']
		return str( res )
#=======================================================================================================
class GetActivityHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		if self.get_pg_version(check_base) == "9.6":
			return make_html_report_with_head( self.make_query( check_base, """select datname, cnt from (
				select datname, count(1) as cnt from pg_stat_activity
				group by datname
				order by cnt desc
				) T
				union all
				select 'Total connections:' as datname, ( select count(1) as cnt from pg_stat_activity )""" ), [ "dbname", "connections" ], "Total connections" ) + \
				make_html_report_with_head( self.make_query( check_base, """select "age"::text as "age", "datid","datname","pid","usename","application_name",
				"client_addr","wait_event_type","wait_event","state","query" from (
					select age(clock_timestamp(), query_start)::text AS "age", "datid","datname","pid","usename","application_name","client_addr","wait_event_type","wait_event","state","query" 
					from pg_stat_activity
					order by "age" desc 
				) T""" ), [ "age", "datid","datname","pid","usename","application_name","client_addr","wait_event_type","wait_event","state","query" ], "pg_stat_activity", ["query"] )
		else:
			return make_html_report_with_head( self.make_query( check_base, """select datname, cnt from (
				select datname, count(1) as cnt from pg_stat_activity
				group by datname
				order by cnt desc
				) T
				union all
				select 'Total connections:' as datname, ( select count(1) as cnt from pg_stat_activity )""" ), [ "dbname", "connections" ], "Total connections" ) + \
				make_html_report_with_head( self.make_query( check_base, """select "age"::text as "age", "datid","datname","pid","usename","application_name",
				"client_addr","waiting","state","query" from (
					select age(clock_timestamp(), query_start)::text AS "age", "datid","datname","pid","usename","application_name","client_addr","waiting","state","query" 
					from pg_stat_activity
					order by "age" desc 
				) T""" ), [ "age", "datid","datname","pid","usename","application_name","client_addr","waiting","state","query" ], "pg_stat_activity", ["query"] )

class GetLocksHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return make_html_report_with_head( self.make_query( check_base, """SELECT t1.blocker_target,
	t1.blocker_pid,
	t1.blocker_mode,
	t1.depth,
	t1.target,
	t1.pid,
	t1.mode,
	t1.seq,
	t1.query
   FROM ( SELECT t.blocker_target,
			t.blocker_pid,
			t.blocker_mode,
			t.depth,
			t.target,
			t.pid,
			t.mode,
			t.seq,
			( SELECT pg_stat_activity.query
				   FROM pg_stat_activity
				  WHERE pg_stat_activity.pid = t.blocker_pid) AS query
		   FROM ( WITH RECURSIVE c(requested, current) AS (
						 VALUES ('AccessShareLock'::text,'AccessExclusiveLock'::text), ('RowShareLock'::text,'ExclusiveLock'::text), ('RowShareLock'::text,'AccessExclusiveLock'::text), ('RowExclusiveLock'::text,'ShareLock'::text), ('RowExclusiveLock'::text,'ShareRowExclusiveLock'::text), ('RowExclusiveLock'::text,'ExclusiveLock'::text), ('RowExclusiveLock'::text,'AccessExclusiveLock'::text), ('ShareUpdateExclusiveLock'::text,'ShareUpdateExclusiveLock'::text), ('ShareUpdateExclusiveLock'::text,'ShareLock'::text), ('ShareUpdateExclusiveLock'::text,'ShareRowExclusiveLock'::text), ('ShareUpdateExclusiveLock'::text,'ExclusiveLock'::text), ('ShareUpdateExclusiveLock'::text,'AccessExclusiveLock'::text), ('ShareLock'::text,'RowExclusiveLock'::text), ('ShareLock'::text,'ShareUpdateExclusiveLock'::text), ('ShareLock'::text,'ShareRowExclusiveLock'::text), ('ShareLock'::text,'ExclusiveLock'::text), ('ShareLock'::text,'AccessExclusiveLock'::text), ('ShareRowExclusiveLock'::text,'RowExclusiveLock'::text), ('ShareRowExclusiveLock'::text,'ShareUpdateExclusiveLock'::text), ('ShareRowExclusiveLock'::text,'ShareLock'::text), ('ShareRowExclusiveLock'::text,'ShareRowExclusiveLock'::text), ('ShareRowExclusiveLock'::text,'ExclusiveLock'::text), ('ShareRowExclusiveLock'::text,'AccessExclusiveLock'::text), ('ExclusiveLock'::text,'RowShareLock'::text), ('ExclusiveLock'::text,'RowExclusiveLock'::text), ('ExclusiveLock'::text,'ShareUpdateExclusiveLock'::text), ('ExclusiveLock'::text,'ShareLock'::text), ('ExclusiveLock'::text,'ShareRowExclusiveLock'::text), ('ExclusiveLock'::text,'ExclusiveLock'::text), ('ExclusiveLock'::text,'AccessExclusiveLock'::text), ('AccessExclusiveLock'::text,'AccessShareLock'::text), ('AccessExclusiveLock'::text,'RowShareLock'::text), ('AccessExclusiveLock'::text,'RowExclusiveLock'::text), ('AccessExclusiveLock'::text,'ShareUpdateExclusiveLock'::text), ('AccessExclusiveLock'::text,'ShareLock'::text), ('AccessExclusiveLock'::text,'ShareRowExclusiveLock'::text), ('AccessExclusiveLock'::text,'ExclusiveLock'::text), ('AccessExclusiveLock'::text,'AccessExclusiveLock'::text)
						), l AS (
						 SELECT ROW(pg_locks.locktype, pg_locks.database, pg_locks.relation::regclass::text, pg_locks.page, pg_locks.tuple, pg_locks.virtualxid, pg_locks.transactionid, pg_locks.classid, pg_locks.objid, pg_locks.objsubid) AS target,
							pg_locks.virtualtransaction,
							pg_locks.pid,
							pg_locks.mode,
							pg_locks.granted
						   FROM pg_locks
						), t AS (
						 SELECT blocker.target::text AS blocker_target,
							blocker.pid AS blocker_pid,
							blocker.mode AS blocker_mode,
							blocked.target::text AS target,
							blocked.pid,
							blocked.mode
						   FROM l blocker
							 JOIN l blocked ON NOT blocked.granted AND blocker.granted AND blocked.pid <> blocker.pid AND NOT blocked.target IS DISTINCT FROM blocker.target
							 JOIN c ON c.requested = blocked.mode AND c.current = blocker.mode
						), r AS (
						 SELECT t_1.blocker_target,
							t_1.blocker_pid,
							t_1.blocker_mode,
							1 AS depth,
							t_1.target,
							t_1.pid,
							t_1.mode,
							(t_1.blocker_pid::text || ','::text) || t_1.pid::text AS seq
						   FROM t t_1
						UNION ALL
						 SELECT blocker.blocker_target,
							blocker.blocker_pid,
							blocker.blocker_mode,
							blocker.depth + 1,
							blocked.target,
							blocked.pid,
							blocked.mode,
							(blocker.seq || ','::text) || blocked.pid::text
						   FROM r blocker
							 JOIN t blocked ON blocked.blocker_pid = blocker.pid
						  WHERE blocker.depth < 1000
						)
				 SELECT r.blocker_target,
					r.blocker_pid,
					r.blocker_mode,
					r.depth,
					r.target,
					r.pid,
					r.mode,
					r.seq
				   FROM r
				  ORDER BY r.seq) t) t1""" ), [ "blocker_target", "blocker_pid", "blocker_mode", "depth", "target", "pid", "mode", "seq", "query" ], "Locks", ["query"] )

class GetLocksPairsHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return make_html_report_with_head( self.make_query( check_base, """
			SELECT waiting.locktype AS waiting_locktype,
			--waiting.relation::regclass AS waiting_table,
			substring(waiting_stm.query from 0 for 400)  AS waiting_query,
			--waiting.mode AS waiting_mode,
			( '<div style="float:left;" link_val="' || waiting.pid::text || '" class="stop_query pg_stat_console_fonts pg_stat_console_button">stop query ' || waiting.pid::text || '</div>' ||
			'<div style="float:left;margin-top:10px;" link_val="' || waiting.pid::text || '" class="kill_connect pg_stat_console_fonts pg_stat_console_button">kill connect ' || waiting.pid::text || '</div>' ) as waiting_pid,	 
			other.locktype AS other_locktype,
			other.relation::regclass AS other_table,
			substring(other_stm.query from 0 for 400) AS other_query,
			other.mode AS other_mode,
			( '<div style="float:left;" link_val="' || other.pid::text || '" class="stop_query pg_stat_console_fonts pg_stat_console_button">stop query ' || other.pid::text || '</div>' ||
			'<div style="float:left;margin-top:10px;" link_val="' || other.pid::text || '" class="kill_connect pg_stat_console_fonts pg_stat_console_button">kill connect ' || other.pid::text || '</div>' ) as other_pid
			FROM pg_locks waiting
			JOIN pg_stat_activity waiting_stm ON waiting_stm.pid = waiting.pid
			JOIN pg_locks other ON waiting.database = other.database AND waiting.relation = other.relation OR waiting.transactionid = other.transactionid
			JOIN pg_stat_activity other_stm ON other_stm.pid = other.pid
			WHERE NOT waiting.granted AND waiting.pid <> other.pid;
			""" ), [ "waiting_locktype","waiting_query","waiting_pid","other_locktype","other_table","other_query","other_mode","other_pid" ], "Locks by pairs", ["other_query","waiting_query"] )

class GetStatementsHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return make_html_report_with_head( self.make_query( check_base, """
			select T.dbid,T.query,T.calls,T.total_time_r,T.blk_read_time_r,T.blk_write_time_r,T.rows,T.shared_blks_hit,T.shared_blks_read,
			T.shared_blks_dirtied
			from
			(
			 SELECT pg_stat_statements.*,
				round(pg_stat_statements.total_time::numeric, 1) as total_time_r,
				round(pg_stat_statements.blk_read_time::numeric, 1) as blk_read_time_r,
				round(pg_stat_statements.blk_write_time::numeric, 1) as blk_write_time_r
			   FROM pg_stat_statements(true)
			) T order by calls desc limit 500
		""" ), [ "dbid","query","calls","total_time","blk_read_time","blk_write_time","rows","shared_blks_hit","shared_blks_read","shared_blks_dirtied" ], "pg_stat_statements", ["query"] )
		
class GetLongQueriesHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return make_html_report_with_head( self.make_query( check_base, """select T.datname, substring(T.query from 0 for 8000), T.age::text, T.pid from (
			SELECT a.datname,
				a.usename,
				a.query,
				a.query_start,
				age(clock_timestamp(), a.query_start) AS age,
				a.pid,
				a.state
			   FROM pg_stat_activity a
			  WHERE a.state = 'active' AND a.pid <> pg_backend_pid()
			  ORDER BY a.query_start		
		) T""" ), [ "datname", "query", "age", "pid" ], "Long queries", ["query"] ) + \
		make_html_report_with_head( self.make_query( check_base, """select T.datname, substring(T.query from 0 for 8000), T.xact_age::text, T.pid, T.state from (
			SELECT a.datname,
				a.usename,
				a.query,
				a.query_start,
				age(clock_timestamp(), a.xact_start) AS xact_age,
				a.pid,
				a.state
			   FROM pg_stat_activity a
			  WHERE a.pid <> pg_backend_pid() and age(clock_timestamp(), a.xact_start) is not null
			  ORDER BY a.xact_start	NULLS LAST	
		) T""" ), [ "datname", "query", "xact_age", "pid", "state" ], "Long transactions", ["query"] )
		
class GetTblSizesHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		html_report = ""	
		
		data = tornado.escape.json_decode(self.request.body)

		for db in dbs_list:
			if db in data["dbs"]:
				html_report = html_report + make_html_report_with_head( self.make_query( db, """select T.nspname, T.relname, T.size, T.idxsize, T.total, T.n_live_tup, T.n_dead_tup, T.rel_oid, T.schema_oid from (
				WITH pg_class_prep AS (
						 SELECT c_1.relname,
							c_1.relnamespace,
							c_1.relkind,
							c_1.oid,
							s.n_live_tup,
							s.n_dead_tup
						   FROM pg_class c_1
							 JOIN pg_stat_all_tables s ON c_1.oid = s.relid
						  ORDER BY s.n_live_tup DESC
						 LIMIT 500
						)
				 SELECT n.nspname,
					c.relname,
					c.relkind AS type,
					pg_size_pretty(pg_table_size(c.oid::regclass)) AS size,
					pg_size_pretty(pg_indexes_size(c.oid::regclass)) AS idxsize,
					pg_size_pretty(pg_total_relation_size(c.oid::regclass)) AS total,
					pg_table_size(c.oid::regclass) AS size_raw,
					pg_indexes_size(c.oid::regclass) AS idxsize_raw,
					pg_total_relation_size(c.oid::regclass) AS total_raw,
					c.n_live_tup,
					c.n_dead_tup,
					c.oid AS rel_oid,
					n.oid AS schema_oid,
					c.relkind
				   FROM pg_class_prep c
					 LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
				  WHERE (n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND n.nspname !~ '^pg_toast'::text AND (c.relkind = ANY (ARRAY['r'::"char", 'i'::"char"]))
				  ORDER BY pg_total_relation_size(c.oid::regclass) DESC
				) T""" ), [ "nspname", "relname", "size", "idxsize", "total", "n_live_tup", "n_dead_tup", "rel_oid", "schema_oid" ], "Table sizes (" + db + ")", ["relname"] )
					
		return html_report

class GetIdxSeqTupFetchHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		html_report = ""

			
		data = tornado.escape.json_decode(self.request.body) 
		
		for db in dbs_list:
			if db in data["dbs"]:	
				html_report = html_report + make_html_report_with_head( self.make_query( db, \
				"select schemaname, relname, seq_scan, seq_tup_read, n_live_tup, n_dead_tup from pg_stat_all_tables order by seq_tup_read desc nulls last limit 50" ), \
				[ "schemaname", "relname", "seq_scan", "seq_tup_read", "n_live_tup", "n_dead_tup" ], "Top seq tup fetched (" + db + ")" ) + \
											make_html_report_with_head( self.make_query( db, \
				"select schemaname, relname, idx_scan, idx_tup_fetch, n_live_tup, n_dead_tup from pg_stat_all_tables order by idx_tup_fetch desc nulls last limit 50" ),\
				[ "schemaname", "relname", "idx_scan", "idx_tup_fetch", "n_live_tup", "n_dead_tup" ], "Top index tup fetched (" + db + ")" )
					
		return html_report

class GetUnusedIdxsHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		unused_idxs_query = """select * from (
				select i.*, pg_size_pretty(pg_relation_size(i.indexrelid::regclass)), pg_relation_size(i.indexrelid::regclass) as  raw_size 
				from pg_stat_all_indexes i
				inner join pg_stat_all_tables s on s.relid = i.relid
				 where i.idx_scan < 1000 and s.n_live_tup > 10000
				 ) T
				order by T.raw_size desc, T.idx_scan asc
				limit 500"""
				
		html_report = ""
	
		
		data = tornado.escape.json_decode(self.request.body) 
		
		for db in dbs_list:
			if db in data["dbs"]:	
				html_report = html_report + make_html_report_with_head( self.make_query( db, unused_idxs_query ), \
				[ "relid","indexrelid","schemaname","relname","indexrelname","idx_scan","idx_tup_read","idx_tup_fetch","pg_size_pretty","raw_size" ], \
				"Unused indexes (" + db + ")", ["indexrelname"] )
		
		return html_report

class GetIndexBloatHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		bloat_query = """WITH btree_index_atts AS (
					SELECT nspname, relname, reltuples, relpages, indrelid, relam,
						regexp_split_to_table(indkey::text, ' ')::smallint AS attnum,
						indexrelid as index_oid, (SELECT pg_get_indexdef (idx.indexrelid)) as def, indisunique, indisprimary, ( select pg_get_constraintdef( pg_constraint.oid ) ) as constraintdef, pg_constraint.oid as conoid, conname
					FROM pg_index as idx
					JOIN pg_class ON pg_class.oid=idx.indexrelid
					JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
					JOIN pg_am ON pg_class.relam = pg_am.oid
					LEFT JOIN pg_constraint ON pg_constraint.connamespace = pg_namespace.oid and conindid = idx.indexrelid
					WHERE pg_am.amname = 'btree' 
					),
				index_item_sizes AS (
					SELECT
					i.nspname, i.relname, i.reltuples, i.relpages, i.relam,
					s.starelid, a.attrelid AS table_oid, index_oid,
					current_setting('block_size')::numeric AS bs,
					/* MAXALIGN: 4 on 32bits, 8 on 64bits (and mingw32 ?) */
					CASE
						WHEN version() ~ 'mingw32' OR version() ~ '64-bit' THEN 8
						ELSE 4
					END AS maxalign,
					24 AS pagehdr,
					/* per tuple header: add index_attribute_bm if some cols are null-able */
					CASE WHEN max(coalesce(s.stanullfrac,0)) = 0
						THEN 2
						ELSE 6
					END AS index_tuple_hdr,
					/* data len: we remove null values save space using it fractionnal part from stats */
					sum( (1-coalesce(s.stanullfrac, 0)) * coalesce(s.stawidth, 2048) ) AS nulldatawidth,
					i.def as def, indisunique, indisprimary, constraintdef, conoid, conname
					FROM pg_attribute AS a
					JOIN pg_statistic AS s ON s.starelid=a.attrelid AND s.staattnum = a.attnum
					JOIN btree_index_atts AS i ON i.indrelid = a.attrelid AND a.attnum = i.attnum
					WHERE a.attnum > 0
					GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, def, indisunique, indisprimary, constraintdef, conoid, conname
				),
				index_aligned AS (
					SELECT maxalign, bs, nspname, relname AS index_name, reltuples,
						relpages, relam, table_oid, index_oid,
					  ( 2 +
						  maxalign - CASE /* Add padding to the index tuple header to align on MAXALIGN */
							WHEN index_tuple_hdr%maxalign = 0 THEN maxalign
							ELSE index_tuple_hdr%maxalign
						  END
						+ nulldatawidth + maxalign - CASE /* Add padding to the data to align on MAXALIGN */
							WHEN nulldatawidth::integer%maxalign = 0 THEN maxalign
							ELSE nulldatawidth::integer%maxalign
						  END
					  )::numeric AS nulldatahdrwidth, pagehdr, def, indisunique, indisprimary, constraintdef, conoid, conname
					FROM index_item_sizes AS s1
				),
				otta_calc AS (
				  SELECT bs, nspname, table_oid, index_oid, index_name, relpages, coalesce(
					ceil((reltuples*(4+nulldatahdrwidth))/(bs-pagehdr::float)) +
					  CASE WHEN am.amname IN ('hash','btree') THEN 1 ELSE 0 END , 0 -- btree and hash have a metadata reserved block
					) AS otta, def, indisunique, indisprimary, constraintdef, conoid, conname
				  FROM index_aligned AS s2
					LEFT JOIN pg_am am ON s2.relam = am.oid
				),
				raw_bloat AS (
					SELECT nspname, c.relname AS table_name, index_name,
						bs*(sub.relpages)::bigint AS totalbytes,
						CASE
							WHEN sub.relpages <= otta THEN 0
							ELSE bs*(sub.relpages-otta)::bigint END
							AS wastedbytes,
						CASE
							WHEN sub.relpages <= otta
							THEN 0 ELSE bs*(sub.relpages-otta)::bigint * 100 / (bs*(sub.relpages)::bigint) END
							AS realbloat,
						pg_relation_size(sub.table_oid) as table_bytes,
						stat.idx_scan as index_scans,  sub.def as def, sub.indisunique as indisunique, sub.indisprimary as indisprimary, sub.constraintdef, sub.conoid, sub.conname
					FROM otta_calc AS sub
					JOIN pg_class AS c ON c.oid=sub.table_oid
					JOIN pg_stat_user_indexes AS stat ON sub.index_oid = stat.indexrelid
				)
				SELECT  nspname as schema_name, table_name, index_name,
						/*round(realbloat, 1) as bloat_pct,*/
						/*wastedbytes as bloat_bytes,*/ pg_size_pretty(wastedbytes::bigint) as bloat_size,
						/*totalbytes as index_bytes,*/ pg_size_pretty(totalbytes::bigint) as index_size,
						/*table_bytes,*/ pg_size_pretty(table_bytes) as table_size,
						index_scans, realbloat, def, conname
				FROM raw_bloat
				WHERE ( realbloat > 30 and wastedbytes > 1000000 ) --and indisprimary = 'false' --and nspname = 'public'
				ORDER BY realbloat DESC;"""
				
		html_report = ""
		data = tornado.escape.json_decode(self.request.body) 
		
		for db in dbs_list:
			if db in data["dbs"]:
				html_report = html_report + make_html_report_with_head( self.make_query( db, bloat_query ), [ "schema_name","table_name","index_name","bloat_size","index_size","table_size","index_scans","realbloat","def","conname" ], "Index Bloat (" + db + ")" )
		return html_report

class GetTableBloatHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		bloat_query = """WITH constants AS (
			-- define some constants for sizes of things
			-- for reference down the query and easy maintenance
			SELECT current_setting('block_size')::numeric AS bs, 23 AS hdr, 8 AS ma
		),
		no_stats AS (
			-- screen out table who have attributes
			-- which dont have stats, such as JSON
			SELECT table_schema, table_name, 
				n_live_tup::numeric as est_rows,
				pg_table_size(relid)::numeric as table_size
			FROM information_schema.columns
				JOIN pg_stat_user_tables as psut
				   ON table_schema = psut.schemaname
				   AND table_name = psut.relname
				LEFT OUTER JOIN pg_stats
				ON table_schema = pg_stats.schemaname
					AND table_name = pg_stats.tablename
					AND column_name = attname 
			WHERE attname IS NULL
				AND table_schema NOT IN ('pg_catalog', 'information_schema')
			GROUP BY table_schema, table_name, relid, n_live_tup
		),
		null_headers AS (
			-- calculate null header sizes
			-- omitting tables which dont have complete stats
			-- and attributes which aren't visible
			SELECT
				hdr+1+(sum(case when null_frac <> 0 THEN 1 else 0 END)/8) as nullhdr,
				SUM((1-null_frac)*avg_width) as datawidth,
				MAX(null_frac) as maxfracsum,
				schemaname,
				tablename,
				hdr, ma, bs
			FROM pg_stats CROSS JOIN constants
				LEFT OUTER JOIN no_stats
					ON schemaname = no_stats.table_schema
					AND tablename = no_stats.table_name
			WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
				AND no_stats.table_name IS NULL
				AND EXISTS ( SELECT 1
					FROM information_schema.columns
						WHERE schemaname = columns.table_schema
							AND tablename = columns.table_name )
			GROUP BY schemaname, tablename, hdr, ma, bs
		),
		data_headers AS (
			-- estimate header and row size
			SELECT
				ma, bs, hdr, schemaname, tablename,
				(datawidth+(hdr+ma-(case when hdr%ma=0 THEN ma ELSE hdr%ma END)))::numeric AS datahdr,
				(maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma ELSE nullhdr%ma END))) AS nullhdr2
			FROM null_headers
		),
		table_estimates AS (
			-- make estimates of how large the table should be
			-- based on row and page size
			SELECT schemaname, tablename, bs,
				reltuples::numeric as est_rows, relpages * bs as table_bytes,
			CEIL((reltuples*
					(datahdr + nullhdr2 + 4 + ma -
						(CASE WHEN datahdr%ma=0
							THEN ma ELSE datahdr%ma END)
						)/(bs-20))) * bs AS expected_bytes,
				reltoastrelid
			FROM data_headers
				JOIN pg_class ON tablename = relname
				JOIN pg_namespace ON relnamespace = pg_namespace.oid
					AND schemaname = nspname
			WHERE pg_class.relkind = 'r'
		),
		estimates_with_toast AS (
			-- add in estimated TOAST table sizes
			-- estimate based on 4 toast tuples per page because we dont have 
			-- anything better.  also append the no_data tables
			SELECT schemaname, tablename, 
				TRUE as can_estimate,
				est_rows,
				table_bytes + ( coalesce(toast.relpages, 0) * bs ) as table_bytes,
				expected_bytes + ( ceil( coalesce(toast.reltuples, 0) / 4 ) * bs ) as expected_bytes
			FROM table_estimates LEFT OUTER JOIN pg_class as toast
				ON table_estimates.reltoastrelid = toast.oid
					AND toast.relkind = 't'
		),
		table_estimates_plus AS (
		-- add some extra metadata to the table data
		-- and calculations to be reused
		-- including whether we cant estimate it
		-- or whether we think it might be compressed
			SELECT current_database() as databasename,
					schemaname, tablename, can_estimate, 
					est_rows,
					CASE WHEN table_bytes > 0
						THEN table_bytes::NUMERIC
						ELSE NULL::NUMERIC END
						AS table_bytes,
					CASE WHEN expected_bytes > 0 
						THEN expected_bytes::NUMERIC
						ELSE NULL::NUMERIC END
							AS expected_bytes,
					CASE WHEN expected_bytes > 0 AND table_bytes > 0
						AND expected_bytes <= table_bytes
						THEN (table_bytes - expected_bytes)::NUMERIC
						ELSE 0::NUMERIC END AS bloat_bytes
			FROM estimates_with_toast
			UNION ALL
			SELECT current_database() as databasename, 
				table_schema, table_name, FALSE, 
				est_rows, table_size,
				NULL::NUMERIC, NULL::NUMERIC
			FROM no_stats
		),
		bloat_data AS (
			-- do final math calculations and formatting
			select current_database() as databasename,
				schemaname, tablename, can_estimate, 
				table_bytes, round(table_bytes/(1024^2)::NUMERIC,3) as table_mb,
				expected_bytes, round(expected_bytes/(1024^2)::NUMERIC,3) as expected_mb,
				round(bloat_bytes*100/table_bytes) as pct_bloat,
				round(bloat_bytes/(1024::NUMERIC^2),2) as mb_bloat,
				table_bytes, expected_bytes, est_rows
			FROM table_estimates_plus
		)
		-- filter output for bloated tables
		SELECT databasename, schemaname, tablename,
			can_estimate,
			est_rows,
			pct_bloat, mb_bloat,
			table_mb
		FROM bloat_data
		-- this where clause defines which tables actually appear
		-- in the bloat chart
		-- example below filters for tables which are either 50%
		-- bloated and more than 20mb in size, or more than 25%
		-- bloated and more than 4GB in size
		WHERE ( pct_bloat >= 50 AND mb_bloat >= 5 )
			OR ( pct_bloat >= 20 AND mb_bloat >= 50 )
		ORDER BY pct_bloat DESC;"""

		html_report = ""
	
		
		data = tornado.escape.json_decode(self.request.body) 
		
		for db in dbs_list:
			if db in data["dbs"]:
				html_report = html_report + make_html_report_with_head( self.make_query( db, bloat_query ), [ "databasename","schemaname","tablename","can_estimate","est_rows","pct_bloat","mb_bloat","table_mb" ], "Table Bloat (" + db + ")", ["tablename"] )
		return html_report		

class GetPGConfigHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return make_html_report_with_head( self.make_query( check_base, \
			"""select name, setting as value, (case when unit = '8kB' then pg_size_pretty(setting::bigint * 1024 * 8) when unit = 'kB' and setting <> '-1' then pg_size_pretty(setting::bigint * 1024) else '' end) as pretty_value, unit, category, short_desc, vartype, boot_val 
			from pg_settings order by category asc""" ), \
			[ "name", "value", "pretty_value", "unit", "category", "short_desc", "vartype", "boot_val" ], "Current cluster configuration", ["short_desc", "name"] )

class GetPGVersionHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		return self.get_pg_version(check_base)

#=======================================================================================================
class GetLogHandler(BaseAsyncHandlerNoParam):
	def get_files_in_interval_dt(self, dir, date_a, date_b ):
		list_files = []
		for dirname,subdirs,files in os.walk( dir ):
			for fname in files:
				if fname[fname.rfind( '.' ):] != "." + pg_log_file_extension:
					continue
				full_path = os.path.join(dirname, fname)
				atime = os.path.getatime(full_path) 
				mtime = os.path.getmtime(full_path) 

				mtime_dt = datetime.fromtimestamp( mtime ) + timedelta(hours=3)		
				dt_from_fname = fname[fname.find( '-' )+1:fname.rfind( '.' )]
				dt_from_fname = dt_from_fname.replace( "_", " " )
				dt_from_fname = dt_from_fname[:13] + ':' + dt_from_fname[13:]
				dt_from_fname = dt_from_fname[:16] + ':' + dt_from_fname[16:]
				atime_dt = datetime.strptime( dt_from_fname, "%Y-%m-%d %H:%M:%S")

				if ( atime_dt >= date_a and atime_dt < date_b ) or ( mtime_dt >= date_a and mtime_dt < date_b ) or ( date_a >= atime_dt and date_a < mtime_dt ) or ( date_b >= atime_dt and date_b < mtime_dt ):
					list_files.append( str( dirname ) + "/" + str( fname ) )
		list_files.sort()
		return list_files

	@contextmanager
	def closing_file(self, fo):
		try:
			yield fo
		except Exception as e:
			logger.log( sys.exc_info()[0], "Error" )
			raise
		finally:
			#logger.log( "call finally closing_file", "Info" )
			fo.close()

	break_scan_log = False
	def post_(self):	
		params = tornado.escape.json_decode(self.request.body) 
		date_a = datetime.strptime( params[ "date_a" ], "%Y-%m-%d %H:%M:%S")
		date_b = datetime.strptime( params[ "date_b" ], "%Y-%m-%d %H:%M:%S")
		
		list_files = self.get_files_in_interval_dt( pg_log_dir, date_a, date_b )
		logger.log( str( list_files ), "Info" )
		
		all_log = []
		for file_name in list_files:
			if self.break_scan_log:
				break;
			fo = None
			try:
				fo = open( file_name, "rb" )
			except IOError as e:
				logger.log( "I/O error({0}): {1}".format(e.errno, e.strerror), "Error" )
				raise
			except:
				logger.log( "Unexpected error:" + str( sys.exc_info()[0] ), "Error" )
				raise
				
			with self.closing_file( fo ) as file:
				for line in file:
					line_len = len( line )
					if line_len > int(pg_log_line_max_len):
						all_log.append( str( line )[:int(pg_log_line_max_len)] )
					else:
						all_log.append( str( line ) )

		str_res = ""

		logger.log( "Start parsing log lines... len( all_log ) = " + str( len( all_log ) ), "Info" )
		for line in all_log:
			if self.break_scan_log:
				break;
			if "error" in params:
				dt_str = line[:line.find(".")]
				try:
					dt = datetime.strptime( dt_str, "b'%Y-%m-%d %H:%M:%S") - timedelta(hours=1)
					if dt >= date_a and dt <= date_b: 
						if line.find( ',ERROR,' ) > -1:
							str_res += line	
				except Exception as e:						
					if line.find( ',ERROR,' ) > -1:
						str_res += line
			elif "fatal" in params:
				dt_str = line[:line.find(".")]
				try:
					dt = datetime.strptime( dt_str, "b'%Y-%m-%d %H:%M:%S") - timedelta(hours=1)
					if dt >= date_a and dt <= date_b: 
						if line.find( ',FATAL,' ) > -1:
							str_res += line	
				except Exception as e:						
					if line.find( ',FATAL,' ) > -1:
						str_res += line
			elif "duration" in params and "reports" not in params:
				duration_val = float(re.search("\d+((.|,)\d+)?", params[ "duration_v" ] ).group())
				great = True if params[ "duration_g" ] == True else False

				dt_str = line[:line.find(".")]
				try:
					dt = datetime.strptime( dt_str, "b'%Y-%m-%d %H:%M:%S") - timedelta(hours=1)
					if dt >= date_a and dt <= date_b: 
						unique_str=re.search(r"duration\:\s\d+((.|,)\d+)?\sms",line)
						if (unique_str is not None):
							digit = re.search("\d+((.|,)\d+)?",str(unique_str.group()))
							x = float( digit.group() )
							if great:
								if x > duration_val:
									str_res += line
							elif x < duration_val:
								str_res += line
						else:
							if "common" in params:
								str_res += line
				except Exception as e:						
					unique_str=re.search(r"duration\:\s\d+((.|,)\d+)?\sms",line)
					if (unique_str is not None):
						digit = re.search("\d+((.|,)\d+)?",str(unique_str.group()))
						x = float( digit.group() )
						if great:
							if x > duration_val:
								str_res += line
						elif x < duration_val:
							str_res += line					
			elif "locked" in params:
				dt_str = line[:line.find(".")]
				try:
					dt = datetime.strptime( dt_str, "b'%Y-%m-%d %H:%M:%S") - timedelta(hours=1)
					if dt >= date_a and dt <= date_b: 
						if ( ( line.find( ' still waiting for ' ) > 0 ) or ( line.find( 'deadlock detected' ) > 0 ) ):
							str_res += line	
				except Exception as e:						
					if ( ( line.find( ' still waiting for ' ) > 0 ) or ( line.find( 'deadlock detected' ) > 0 ) ):
						str_res += line			
			else:
				dt_str = line[:line.find(".")]
				try:
					dt = datetime.strptime( dt_str, "b'%Y-%m-%d %H:%M:%S") - timedelta(hours=1)
					if dt >= date_a and dt <= date_b: 
						str_res += line		
				except Exception as e:						
					str_res += line
		logger.log( "End parsing logger.log lines...", "Info" )
		str_res = html.escape( str_res )
		if str_res.find("""b&#x27;""") == 0:
			str_res = str_res[len("""b&#x27;"""):]
			
		str_res = str_res.replace( """\\n&#x27;b&#x27;""", "<br></br>" )
		str_res = str_res.replace( """b&#x27;""", "<br></br>" ) 

		if hide_password_in_queries:
			str_res = re.sub(r"password=\w+", '', str_res) 
		if hide_host_in_queries:
			str_res = re.sub(r"host=\w+", '', str_res)
		return str_res	

	def on_connection_close(self):
		logger.log( "try cancel GetLogHandler...", "Info" )
		self.break_scan_log = True

class GetListLogFilesHandler(BaseAsyncHandlerNoParam):
	def get_files_in_interval_dt(self, dir, date_a, date_b ):
		list_files = []
		for dirname,subdirs,files in os.walk( dir ):
			for fname in files:
				if fname[fname.rfind( '.' ):] != "." + pg_log_file_extension:
					continue
				full_path = os.path.join(dirname, fname)
				atime = os.path.getatime(full_path) 
				mtime = os.path.getmtime(full_path) 

				mtime_dt = datetime.fromtimestamp( mtime ) + timedelta(hours=3)		
				dt_from_fname = fname[fname.find( '-' )+1:fname.rfind( '.' )]
				dt_from_fname = dt_from_fname.replace( "_", " " )
				dt_from_fname = dt_from_fname[:13] + ':' + dt_from_fname[13:]
				dt_from_fname = dt_from_fname[:16] + ':' + dt_from_fname[16:]
				atime_dt = datetime.strptime( dt_from_fname, "%Y-%m-%d %H:%M:%S")

				if ( atime_dt >= date_a and atime_dt < date_b ) or ( mtime_dt >= date_a and mtime_dt < date_b ) or ( date_a >= atime_dt and date_a < mtime_dt ) or ( date_b >= atime_dt and date_b < mtime_dt ):
					list_files.append( str( dirname ) + "/" + str( fname ) )
		list_files.sort()
		return list_files
		
	def post_(self):

		params = tornado.escape.json_decode(self.request.body) 
		date_a = datetime.strptime( params[ "date_a" ], "%Y-%m-%d %H:%M:%S")
		date_b = datetime.strptime( params[ "date_b" ], "%Y-%m-%d %H:%M:%S")
		
		list_files = self.get_files_in_interval_dt( pg_log_dir, date_a, date_b )
		logger.log( str( list_files ), "Info" )
		report_data = []
		for file_name in list_files:
			link = """<div style="float:left;" link_val=\"""" + os.path.basename( file_name ) + """\" class="log_download pg_stat_console_fonts pg_stat_console_button">download</div>"""
			report_data.append( [ os.path.basename( file_name ), time.ctime(os.path.getmtime(file_name)), str( os.path.getsize(file_name) >> 20 ) + " MB", link ] )
		return make_html_report_with_head( report_data, [ "File name","Modified","Size","Link" ], "List log files" )
			
class DownloadLogFileHandler(BaseAsyncHandlerNoParam):
	@contextmanager
	def closing_file(self, fo):
		try:
			yield fo
		except Exception as e:
			logger.log( sys.exc_info()[0], "Error" )
			raise
		finally:
			logger.log( "call finally closing_file", "Info" )
			fo.close()
			
	def post_(self):
		params = tornado.escape.json_decode(self.request.body) 

		logger.log( "Start gzip file..." + params[ "file_name" ], "Info" )
		with self.closing_file( open( pg_log_dir + '/' + params[ "file_name" ], 'rb') ) as source_file:
			with self.closing_file( gzip.open( current_dir + "download/" + params[ "file_name" ] + '.gz', 'wb') ) as dest_file:
				dest_file.writelines(source_file)
		logger.log( "Finish gzip file.", "Info" )
		return '/download/' + params[ "file_name" ] + '.gz'

#=======================================================================================================
class GetOldConnsHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		params = tornado.escape.json_decode(self.request.body)
		
		html_report = ""

		if self.get_pg_version(check_base) == "9.6":
			html_report = make_html_report_with_head( self.make_query( check_base, """select age(clock_timestamp(), query_start) AS "query_age", 
				age(clock_timestamp(), xact_start) AS "xact_age",
				age(clock_timestamp(), backend_start) AS "backend_age", state, "wait_event_type","wait_event", datname, usename, application_name, client_addr, query,
				( '<div style="float:left;margin-top:10px;" link_val="' || pid::text || '" class="kill_connect pg_stat_console_fonts pg_stat_console_button">kill connect ' || pid::text || '</div>' ) as pid			 
				from pg_stat_activity 
				where clock_timestamp()-query_start > interval '""" + params[ "conn_age" ] + """ minutes'
				order by "query_age" desc""" ), [ "query_age", "xact_age", "backend_age", "state", "wait_event_type", "wait_event", "datname", "usename", "application_name" , "client_addr", "query", "pid" ], "All old unused connections", ["query"] )
		else:
			html_report = make_html_report_with_head( self.make_query( check_base, """select age(clock_timestamp(), query_start) AS "query_age", 
				age(clock_timestamp(), xact_start) AS "xact_age",
				age(clock_timestamp(), backend_start) AS "backend_age", state, waiting, datname, usename, application_name, client_addr, query,
				( '<div style="float:left;margin-top:10px;" link_val="' || pid::text || '" class="kill_connect pg_stat_console_fonts pg_stat_console_button">kill connect ' || pid::text || '</div>' ) as pid			 
				from pg_stat_activity 
				where clock_timestamp()-query_start > interval '""" + params[ "conn_age" ] + """ minutes'
				order by "query_age" desc""" ), [ "query_age", "xact_age", "backend_age", "state", "waiting", "datname", "usename", "application_name" , "client_addr", "query", "pid" ], "All old unused connections", ["query"] )
		
		return html_report

class GetConnManagementHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		if self.get_pg_version(check_base) == "9.6":
			return make_html_report_with_head( self.make_query( check_base, """SELECT T."wait_event_type",T."wait_event",T.state,T.age, T.datname, T.usename, T.application_name, T.query, T.query_start, T.pid, T.pid2 
			from ( select a."wait_event_type",a."wait_event",a.state, age(clock_timestamp(), a.query_start)::text AS age,
				a.datname,
				a.usename,
				a.application_name,
				substring(a.query from 0 for 400) as query,
				--a.query,
				a.query_start,
				( case when a.state = 'active' then '<div style="float:left;" link_val="' || a.pid::text || '" class="stop_query pg_stat_console_fonts pg_stat_console_button">stop query '  || a.pid::text ||  '</div>'
				else a.pid::text end ) as pid,
				('<div style="float:left;" link_val="' || a.pid::text || '" class="kill_connect pg_stat_console_fonts pg_stat_console_button">kill connect ' || a.pid::text || '</div>') as pid2,
				age(clock_timestamp(), a.query_start) as age_sort
			   FROM pg_stat_activity a
			  WHERE a.pid <> pg_backend_pid()
			  ORDER BY a.state asc, age_sort desc ) T""" ), [ "wait_event_type","wait_event", "state", "age", "datname", "usename", "app_name", "query", "query_start", "pid", "pid" ], "All connections", ["query"] )
		else:
			return make_html_report_with_head( self.make_query( check_base, """SELECT T.waiting,T.state,T.age, T.datname, T.usename, T.application_name, T.query, T.query_start, T.pid, T.pid2 
			from ( select a.waiting,a.state, age(clock_timestamp(), a.query_start)::text AS age,
				a.datname,
				a.usename,
				a.application_name,
				substring(a.query from 0 for 400) as query,
				--a.query,
				a.query_start,
				( case when a.state = 'active' then '<div style="float:left;" link_val="' || a.pid::text || '" class="stop_query pg_stat_console_fonts pg_stat_console_button">stop query '  || a.pid::text ||  '</div>'
				else a.pid::text end ) as pid,
				('<div style="float:left;" link_val="' || a.pid::text || '" class="kill_connect pg_stat_console_fonts pg_stat_console_button">kill connect ' || a.pid::text || '</div>') as pid2,
				age(clock_timestamp(), a.query_start) as age_sort
			   FROM pg_stat_activity a
			  WHERE a.pid <> pg_backend_pid()
			  ORDER BY a.state asc, age_sort desc ) T""" ), [ "waiting", "state", "age", "datname", "usename", "app_name", "query", "query_start", "pid", "pid" ], "All connections", ["query"] )
		
			  
class ProcessCommonFuncs():
	def get_command_by_pid(self, pid):
		cmd = subprocess.Popen("cat /proc/" + str( pid ) + "/cmdline",shell=True,stdout=subprocess.PIPE)
		result = ""
		for line in cmd.stdout:	
			result = line.decode('utf8')
		return result

class GetServerProcessesHandler(BaseAsyncHandlerNoParam,ProcessCommonFuncs):
	def make_proc_data(self):
		result = []
		cmd = subprocess.Popen('top -b -n 1 -c -u postgres',shell=True,stdout=subprocess.PIPE)
		list_begin = False
		for line in cmd.stdout:
			columns = line.decode('utf8').split()
			if list_begin and len( columns ) > 11:
				result.append( [ columns[0], columns[1],columns[4],columns[5],columns[6],columns[7],columns[8],columns[9],columns[10], self.get_command_by_pid( columns[0] ) ] )
			if len( columns ) > 11 and columns[0] == 'PID':
				list_begin = True
		return result
		
	def post_(self):
		return make_html_report_with_head( self.make_proc_data(), [ "PID", "USER", "VIRT", "RES", "SHR", "S", "%CPU", "%MEM", "TIME+", "COMMAND" ], "Server processes", ["COMMAND"] )

class GetIOServerProcessesHandler(BaseAsyncHandlerNoParam,ProcessCommonFuncs):
	def make_proc_data(self):
		result = []
		cmd = subprocess.Popen('iotop -o -b -n 1',shell=True,stdout=subprocess.PIPE)
		list_begin = False
		for line in cmd.stdout:
			columns = line.decode('utf8').split()
			if list_begin and len( columns ) >= 10:
				result.append( [ columns[0], columns[1],columns[2],columns[3] + " " + columns[4], columns[5] + " " + columns[6],columns[7] + " " + columns[8],columns[9]+ " " +columns[10], self.get_command_by_pid( columns[0] ) ] )
			if len( columns ) >= 10 and columns[0] == 'TID':
				list_begin = True

		return result
		
	def post_(self):
		return make_html_report_with_head( self.make_proc_data(), [ "TID", "PRIO", "USER", "DISK READ", "DISK WRITE", "SWAPIN", "IO", "COMMAND" ], "iotop processes", ["COMMAND"] )
		
class StopQueryHandler(BaseAsyncHandlerNoParam):
	def post_(self):
		params = tornado.escape.json_decode(self.request.body)  

		if params["command"] == 'cancel':
			result = self.make_query( check_base, """select pg_cancel_backend(""" + params["pid"] + """) as res""" )
			logger.log( "Call pg_cancel_backend for pid " + params["pid"], "Info" )
			for row in result:
				backend_result = row['res']
				return str( backend_result )

		if params["command"] == 'kill':
			result = self.make_query( check_base, """select pg_terminate_backend(""" + params["pid"] + """) as res""" )
			logger.log( "Call pg_terminate_backend for pid " + params["pid"], "Info" )
			for row in result:
				backend_result = row['res']
				return str( backend_result )

		return 'true'

class GetMaintenanceStatusHandler(BaseAsyncHandlerNoParam):   
	def post_(self):
		result = self.make_query( check_base, """select exists( select 1 from pg_stat_activity 
			where application_name <> '""" + application_name + """' and pid <> pg_backend_pid() and state = 'active' and ( 
				query ilike '%create%index%' or 
				query ilike '%alter%table%' or 
				query ilike '%drop%table%' or	 
				query ilike '%truncate%' or 
				query like '%COPY%'  or
				query like '%reindex%'  or	
				query like '%cluster%'  or		
				query like '%vacuum%'  or
				query like '%analyze%'		
			) ) as  result""" )

		res = None
		for row in result:
			res = row['result']
		self.set_header('Content-Type', 'application/json')
		return json.dumps(res, ensure_ascii=False).encode('utf8') 

class GetMaintenanceTasksHandler(BaseAsyncHandlerNoParam):   
	def post_(self):
		if self.get_pg_version(check_base) == "9.6":
			return make_html_report_with_head( self.make_query( check_base, """select age(clock_timestamp(), query_start) AS "query_age", 
				age(clock_timestamp(), xact_start) AS "xact_age", state, wait_event_type, wait_event, datname, usename, application_name, client_addr, query, pid
				from pg_stat_activity 
				where application_name <> '""" + application_name + """' and pid <> pg_backend_pid() and state = 'active' and ( 
					query ilike '%create%index%' or 
					query ilike '%alter%table%' or 
					query ilike '%drop%table%' or	 
					query ilike '%truncate%' or 
					query like '%COPY%'  or
					query like '%reindex%'  or	
					query like '%cluster%'  or		
					query like '%vacuum%'  or
					query like '%analyze%'		
				)			
				order by "query_age" desc""" ), [ "query_age", "xact_age", "state", "wait_event_type", "wait_event", "datname", "usename", "application_name", "client_addr", "query", "pid" ], "Runned maintenance operations", ["query"] )			
		else:
			return make_html_report_with_head( self.make_query( check_base, """select age(clock_timestamp(), query_start) AS "query_age", 
				age(clock_timestamp(), xact_start) AS "xact_age", state, waiting, datname, usename, application_name, client_addr, query, pid
				from pg_stat_activity 
				where application_name <> '""" + application_name + """' and pid <> pg_backend_pid() and state = 'active' and ( 
					query ilike '%create%index%' or 
					query ilike '%alter%table%' or 
					query ilike '%drop%table%' or	 
					query ilike '%truncate%' or 
					query like '%COPY%'  or
					query like '%reindex%'  or	
					query like '%cluster%'  or		
					query like '%vacuum%'  or
					query like '%analyze%'		
				)			
				order by "query_age" desc""" ), [ "query_age", "xact_age", "state", "waiting", "datname", "usename", "application_name", "client_addr", "query", "pid" ], "Runned maintenance operations", ["query"] )			

				
application = tornado.web.Application([ 
			(r"/(.*\.gz)", PgStatConsoleStaticFileHandler,{"path": current_dir }),  
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
			('/getPGConfig', GetPGConfigHandler),
			('/getPGVersion', GetPGVersionHandler)
	])

application.listen(int(port))
logger.log( "Application is ready to work! Port " + str(port), "Info" )
logger.log( "Allowed hosts " + str( allow_host_list ), "Info" )

IOLoop.instance().start()

