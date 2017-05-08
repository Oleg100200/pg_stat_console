import re
import os
import resource
#=======================================================================================================
def limit_memory(maxsize):
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