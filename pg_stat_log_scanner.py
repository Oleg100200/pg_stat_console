from threading import Thread
import threading
import postgresql
import sys
from datetime import datetime, timedelta
import os
import re
import time
import configparser
from operator import itemgetter

from contextlib import contextmanager
from pgstatlogger import PSCLogger
#=======================================================================================================
current_dir = os.path.dirname(sys.argv[0]) + '/'
#=======================================================================================================
#init config
config = configparser.RawConfigParser()
config.optionxform = lambda option: option
config.read( current_dir + 'conf/pg_stat_log_scanner.conf')
#=======================================================================================================
def read_conf_param_value( raw_value, boolean = False ):
	#case 1:	param = 100 #comment
	#case 2:	param = "common args" #comment
	#case 3:	param = some text #comment
	value_res = raw_value
	quotes = re.findall("""\"[^"]*\"""", raw_value)
	if len( quotes ) > 0:
		value_res = quotes[0]
		value_res = value_res.replace("\"", "")
	else:
		if raw_value.find("#") > -1:
			value_res = raw_value[0:raw_value.find("#")-1]
		value_res = value_res.strip(' \t\n\r')
	
	if boolean:
		return True if value_res in [ '1', 't', 'true', 'True'] else False
	
	return value_res
#=======================================================================================================
#vars from config
sys_stat_conn_str = read_conf_param_value( config['sys_stat']['sys_stat'] )
application_name = read_conf_param_value( config['main']['application_name'] )

pg_log_file_extension = read_conf_param_value( config['main']['pg_log_file_extension'] )
pg_log_dir = read_conf_param_value( config['main']['pg_log_dir'] )
sleep_interval = read_conf_param_value( config['main']['sleep_interval'] )
preload_logs_interval = int(read_conf_param_value( config['main']['preload_logs_interval']))

pg_log_line_max_len = read_conf_param_value( config['main']['pg_log_line_max_len'] )
time_zone = read_conf_param_value( config['main']['time_zone'] )

node_name = read_conf_param_value( config['main']['node_name'] )
node_descr = read_conf_param_value( config['main']['node_descr'] )
node_host = read_conf_param_value( config['main']['node_host'] )
#=======================================================================================================
logger = PSCLogger( application_name )
logger.start()
#=======================================================================================================
class LogScanner(Thread):
	def get_files_in_interval_dt( self, dir, date_a, date_b ):
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

				if 	( atime_dt >= date_a and atime_dt < date_b ) or ( mtime_dt >= date_a and mtime_dt < date_b ) or \
					( date_a >= atime_dt and date_a < mtime_dt ) or ( date_b >= atime_dt and date_b < mtime_dt ):
					list_files.append( str( dirname ) + "/" + str( fname ) )
		list_files.sort()
		return list_files

	def get_date_pos_in_log_map( self, map, curr_pos ):
		val = max(map,key=itemgetter(1))[1] 
		for v in map:
			if v[0] != 'p' and v[0] != 'l' and v[1] < val and v[1] > curr_pos:
				val = v[1]
		return val

	def get_prev_date_pos_in_log_map( self, map, curr_pos ):
		val = 0
		for v in map:
			if v[0] != 'p' and v[0] != 'l' and v[1] > val and v[1] < curr_pos:
				val = v[1]
		return val	

	def get_prev_link_in_log_map( self, map, curr_pos ):
		val = 0
		link = ""	
		for v in map:
			if v[0] == 'l' and v[1] > val and v[1] < curr_pos:
				val = v[1]
				link = v[3]			
		return link	

	def get_query_by_link( self, map, link ):
		links = []
		for v in map:
			if v[0] == 'l' and v[3] == link:
				links.append( v )
		return links

	def get_link( self, full_list, val ):
		pos = [y[1] for y in full_list].index(val)
		if len( full_list ) >= pos + 1:
			return full_list[ pos + 1 ][3]
		return -1

	@contextmanager
	def closing_file(self, fo):
		try:
			yield fo
		except Exception as e:
			logger.log( sys.exc_info()[0], "Error" )
			raise
		finally:
			#logger.log( "Call finally closing_file", "Info" )
			fo.close()

	def init_sys_stat( self, conn ):
		conn.execute( """set application_name = '""" + application_name + """'""" )
		conn.execute( """select public.psc_init_node('""" + node_name + """', '""" + node_descr + """', '""" + node_host + """')""" )
		conn.execute( """set extra_float_digits = 3;""" )
		conn.execute( """set timezone = '""" + time_zone + """';""" )
		query = conn.prepare( """select public.psc_get_node('""" + node_name + """', '""" + node_descr + """', '""" + node_host + """')""" )
		shm_name_res = query()
		conn.execute( """set search_path = 'n""" + str( shm_name_res[0][0] ) + """', 'public'""" )		
	#=======================================================================================================
	def __init__(self):
		Thread.__init__(self)

	def run(self):
		first_run = True
		while True:
			try:
				if first_run:
					date_a = datetime.now() - ( timedelta( seconds = int( sleep_interval ) + 300 + int( preload_logs_interval ) * 60 * 60 ) )
				else:
					date_a = datetime.now() - ( timedelta( seconds = int( sleep_interval ) + 300 ) )

				first_run = False

				date_b = datetime.now()
				list_files = self.get_files_in_interval_dt( pg_log_dir, date_a, date_b )
				logger.log( "Start iteration. Files: " + str( list_files ), 'Info' )
			except Exception as e:
				logger.log( "get_files_in_interval_dt error: " + str( e ), "Error" )

			db_pg_stat = None

			try:
				db_pg_stat = postgresql.open( sys_stat_conn_str )
				self.init_sys_stat( db_pg_stat )

				for file_name in list_files:
					logger.log( "Processing... " + file_name, 'Info' )
					fo = open( file_name, "r" )
					str_val = ""
					log_lines = [] 
					
					with self.closing_file( fo ) as file:
						for line in file:
							line_len = len( line )
							if line_len > int(pg_log_line_max_len):
								log_lines.append( str( line )[:int(pg_log_line_max_len)] )
							else:
								log_lines.append( str( line ) )	
					
					for line in log_lines:
						str_val += str( line )
					
					if len( str_val ) < 1:
						continue

					links=re.finditer(r"\,\d+\/\d+\,\d+\,LOG\,\d+", str_val)
					plans=re.finditer(r"duration\:\s\d+((.|,)\d+)?\sms\s\splan\:", str_val)
					dates=re.finditer(r"20\d{2}(-|\/)((0[1-9])|(1[0-2]))(-|\/)((0[1-9])|([1-2][0-9])|(3[0-1]))(\s)(([0-1][0-9])|(2[0-3])):([0-5][0-9]):([0-5][0-9])\.([0-9][0-9][0-9])", str_val)
					
					full_map = []
					log_map = []
					
					#======================================
					for m in links:
						full_map.append( [ "l", m.span()[0], m.span()[1], str_val[ m.span()[0]:m.span()[1]] ] )
						
					for m in plans:
						full_map.append( [ "p", m.span()[0], m.span()[1], str_val[ m.span()[0]:m.span()[1]] ] )
						
					for m in dates:
						full_map.append( [ "d", m.span()[0], m.span()[1], str_val[ m.span()[0]:m.span()[1]] ] )
					#======================================
					
					full_map_sorted = sorted(full_map, key=lambda x: x[1], reverse=False)

					ps_queries_and_plans = db_pg_stat.prepare("""
							INSERT INTO psc_queries_and_plans(
									 dt, duration, db_id, query, plan, io_read_time, cost_v, shared_hit_v, read_v, dirtied_v, total_blks_size )
								VALUES (
									(($1::text)::timestamp with time zone), $2::double precision, (select psc_get_db($3::text)), $4::text, $5::text, $6::double precision, 
										$7::double precision, $8::bigint, $9::bigint, $10::bigint, (select pg_size_pretty((($8::bigint + $9::bigint + $10::bigint)*8192)::bigint)) 
								);""")
						
					ps_queries_and_plans_check = db_pg_stat.prepare("""
							select exists( select 1 from psc_queries_and_plans where dt = (($1::text)::timestamp with time zone) and 
								duration = $2::double precision and query = $3::text )""")

					for v in full_map_sorted:
						if v[ 0 ] == "p":

							txt_plan = str_val[ self.get_prev_date_pos_in_log_map( full_map_sorted, v[ 1 ] ):self.get_date_pos_in_log_map( full_map_sorted, v[ 1 ] ) ]
							txt_query = ""
							
							links = self.get_query_by_link( full_map_sorted, self.get_prev_link_in_log_map( full_map_sorted, v[ 1 ] ) )
							if len(links) == 2:
								txt_query = str_val[ self.get_prev_date_pos_in_log_map( full_map_sorted, \
									links[ 0 ][1] ):self.get_date_pos_in_log_map( full_map_sorted, links[0][ 1 ] ) ]
								if txt_query.find("ms  plan:") > -1:
									txt_query = str_val[ self.get_prev_date_pos_in_log_map( full_map_sorted, \
										links[ 1 ][1] ):self.get_date_pos_in_log_map( full_map_sorted, links[1][ 1 ] ) ]
							else:
								continue

							#-----------------------------------------------------------------------------------
							dt = "2000-01-01 00:00:00"
							dt_str=re.search(r"20\d{2}(-|\/)((0[1-9])|(1[0-2]))(-|\/)((0[1-9])|([1-2][0-9])|(3[0-1]))(\s)(([0-1][0-9])|(2[0-3])):([0-5][0-9]):([0-5][0-9])\.([0-9][0-9][0-9])",txt_query)
							if (dt_str is not None):
								dt = dt_str.group()
								
							#-----------------------------------------------------------------------------------			

							#-----------------------------------------------------------------------------------
							dbname = "unknown"
							pos_first = txt_query.find('","')
							if pos_first > 0:
								dbname =txt_query[ pos_first + 3: txt_query.find('",', pos_first + 3, len( txt_query ) ) ]
							#-----------------------------------------------------------------------------------
							
							shared_hit = 0
							read = 0
							dirtied = 0
							io_read_time = 0
							cost = 0
							duration = 0
							
							duration_str=re.finditer(r"duration\:\s\d+((.|,)\d+)?\sms", txt_plan)
							cost_str=re.finditer(r"cost\=\d+((.|,)\d+)?\.\.\d+((.|,)\d+)?\s", txt_plan)
							io_read_time_str=re.finditer(r"I\/O\sTimings\:\sread\=\d+((.|,)\d+)?", txt_plan)
							shared_hit_str=re.finditer(r"shared\shit\=\d+((.|,)\d+)?", txt_plan)
							read_str=re.finditer(r"read\=\d+((.|,)\d+)?", txt_plan)
							dirtied_str=re.finditer(r"dirtied\=\d+((.|,)\d+)?", txt_plan)

							durations = []
							for m in duration_str:
								sub_str = txt_plan[m.span()[0]:m.span()[1]]
								val = re.finditer(r"\d+((.|,)\d+)?", sub_str)
								for v in val:
									durations.append( float( sub_str[v.span()[0]:v.span()[1]] ) )
							if len( durations ) > 0:						
								duration = max( durations )
								
							costs = []
							for m in cost_str:
								sub_str = txt_plan[m.span()[0]:m.span()[1]]
								val = re.finditer(r"\d+((.|,)\d+)?", sub_str)
								for v in val:
									costs.append( float( sub_str[v.span()[0]:v.span()[1]] ) )
							if len( costs ) > 0:						
								cost = max( costs )

							shared_hits = []
							for m in shared_hit_str:
								sub_str = txt_plan[m.span()[0]:m.span()[1]]
								val = re.finditer(r"\d+((.|,)\d+)?", sub_str)
								for v in val:
									shared_hits.append( float( sub_str[v.span()[0]:v.span()[1]] ) )
							if len( shared_hits ) > 0:
								shared_hit = max( shared_hits )

							io_read_times = []
							for m in io_read_time_str:
								sub_str = txt_plan[m.span()[0]:m.span()[1]]
								val = re.finditer(r"\d+((.|,)\d+)?", sub_str)
								for v in val:
									io_read_times.append( float( sub_str[v.span()[0]:v.span()[1]] ) )
							if len( io_read_times ) > 0:
								io_read_time = max( io_read_times )	
								
							reads = []
							for m in read_str:
								sub_str = txt_plan[m.span()[0]:m.span()[1]]
								val = re.finditer(r"\d+((.|,)\d+)?", sub_str)
								for v in val:
									reads.append( float( sub_str[v.span()[0]:v.span()[1]] ) )
							if len( reads ) > 0:
								if io_read_time in reads:
									reads.remove(io_read_time)
								read = max( reads )
								
							dirtieds = []
							for m in dirtied_str:
								sub_str = txt_plan[m.span()[0]:m.span()[1]]
								val = re.finditer(r"\d+((.|,)\d+)?", sub_str)
								for v in val:
									dirtieds.append( float( sub_str[v.span()[0]:v.span()[1]] ) )
							if len( dirtieds ) > 0:
								dirtied = max( dirtieds )			

							if not ps_queries_and_plans_check.first(str(dt), float(duration), str(txt_query) ):
								query_result = ps_queries_and_plans.first(str(dt), float(duration), str(dbname), str(txt_query), \
									str(txt_plan), float(io_read_time), float(cost), int(float(shared_hit)), int(float(read)), int(float(dirtied)) )
								logger.log( "Writed query at " + str(dt), "Info" )	
							
			except Exception as e:
				logger.log( "Connection db_pg_stat error: " + str( e ), "Error" )
				time.sleep( int( sleep_interval ) )
			finally:
				if db_pg_stat is not None:
					if not db_pg_stat.closed:
						db_pg_stat.close()
				logger.log('Finish iteration! Sleep on ' + str( sleep_interval ) + " seconds...", "Info" )
				time.sleep( int( sleep_interval ) )

log_scanner = LogScanner()
log_scanner.start()

logger.log( "=======> pg_stat_log_scanner runned!", "Info" )