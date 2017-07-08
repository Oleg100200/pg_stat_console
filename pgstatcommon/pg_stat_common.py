import re
import os
import sys

resource_avaible = True
try:
	import resource
except ImportError:
	resource_avaible = False

#=======================================================================================================
def limit_memory(maxsize):
	global resource_avaible
	if resource_avaible:
		soft, hard = resource.getrlimit(resource.RLIMIT_AS)
		resource.setrlimit(resource.RLIMIT_AS, (maxsize, hard))
#=======================================================================================================
def read_conf_param_value( raw_value, boolean = False ):
	#case 1:	param = 100 #comment
	#case 2:	param = "common args" #comment
	#case 3:	param = some text #comment
	#case 4:	param = some text #"comment"
	value_res = raw_value
	if value_res.find("#") > -1:
		value_res = value_res[0:value_res.find("#")-1]
	
	quotes = re.findall("""\"[^"]*\"""", value_res)
	
	if len( quotes ) > 0:
		value_res = quotes[0]
		value_res = value_res.replace("\"", "")
	else:
		value_res = value_res.strip(' \t\n\r')
	
	if boolean:
		return True if value_res in [ '1', 't', 'true', 'True'] else False
	
	return value_res
#=======================================================================================================
def prepare_dirs():
	dirs = [ '/log/', '/download/' ]
	for v in dirs:
		if not os.path.exists( os.getcwd() + v[0] ):
			os.makedirs( os.getcwd() + v[0] )
#=======================================================================================================
def make_html_report_with_head( data, columns, head_name, query_column=None ):
	html_report = ""
	html_columns = ""
	for v in columns:
		if query_column is not None:
			if str(v) in query_column:
				html_columns = html_columns + """<th style="width:320px;">""" + str(v) + "</th>"
			else:
				html_columns = html_columns + "<th>" + str(v) + "</th>"
		else:
			html_columns = html_columns + "<th>" + str(v) + "</th>"
	
	html_rows = ""
	for v in data:
		html_col_vals = ""
		for val in v:
			val_res = str(val)
			if 'hide_password_in_queries' in globals() and hide_password_in_queries:
				val_res = re.sub(r"password=\w+", '', val_res) 
			if 'hide_host_in_queries' in globals() and hide_host_in_queries:
				val_res = re.sub(r"host=\w+", '', val_res)			 
			html_col_vals = html_col_vals + """<td>""" + str( val_res ) + """</td>"""
		html_row = """<tr>""" + html_col_vals + """</tr>"""
		html_rows = html_rows + html_row
	
	html_table = """<div class="report_table pg_stat_console_fonts_on_white scrollable_obj"><h2 style ="text-align: center;font-size: 16px;">""" + head_name + """</h2><table style="table-layout: fixed;word-wrap:break-word;" class="bordered tablesorter"><thead><tr>""" + html_columns + """</tr></thead>""" + html_rows + """</table></div>"""

	html_report = html_report + str( html_table )
	return html_report
#=======================================================================================================
do_unlock = True
def create_lock(application_name):
	global do_unlock
	import atexit
	import signal
	from tornado.ioloop import IOLoop
	from pgstatlogger import PSCLogger
	@atexit.register
	def unlock():
		global do_unlock
		if do_unlock:
			try:
				do_unlock = False
				print( application_name + " stopped!" )
				os.remove( application_name + ".lock" )
			except IOError as e:
				print( "can't unlock " + application_name + ".lock" )
			finally:
				IOLoop.instance().stop()
				PSCLogger.instance().stop()
				sys.exit(0)
	def handler(signum, frame):
		unlock()
	signal.signal(signal.SIGTERM, handler)	
	try:
		fd = os.open( application_name + ".lock", os.O_CREAT|os.O_EXCL)
	except IOError as e:
		print( application_name + " already runned!" )
		do_unlock = False
		exit()
#=======================================================================================================
