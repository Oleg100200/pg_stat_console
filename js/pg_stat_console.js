var selected_menu_elem = { name:"", auto_refresh: false };
var details_closed = true;
var load_process = [];
var load_process_closed = true;
var refresh_interval = 60;
var current_xhr = [];
var auto_refresh_counter = 0;
var title_val = "";
var current_node_name = "";
var current_node_info = [];
var table_num_viewed = 1;
var current_user_type = "";
var user_name_val = "";
var all_charts_on_page = [];
var left_menu;
var user_dashboard;
var progress_visisble = false;
var progress_hidden = true;
var demo_dt_a = "";
var demo_dt_b = "";


var dashboard_dict = [['getCPUStat','CPU load'],
['getMemUsageStat','Memory usage'],
['getDiskUtilStat','Disk utilization'],
['getDiskUsageStat','Disk usage'],
['getWRQMRRQMStat','rrqm/s wrqm/s'],
['getWRStat','r/s w/s'],
['getRSecWSecStat','rMB/s wMB/s'],
['getAVGRQStat','avgrq-sz'],
['getAVGQUStat','avgqu-sz'],
['getAWaitStat','await'],
['getNetworkTrafficStat','Network Traffic'],
['getNetworkPacketsStat','Network Packets'],
['getNetworkErrorsStat','Network Errors'],
['getReadStat','heap_blks_read_per_sec'],
['getWriteStat','_tup_per_sec'],
['getTupStat','tup_fetch_sum'], ['getTupStat','idx_tup_fetch_per_sec'], ['getTupStat','seq_tup_read_per_sec'],
['getIndexStat','reads / fetched'],['getIndexStat','reads / scans'],['getIndexStat','fetched / scans'],
['getQueryDurations','Query durations in sec'],
['getQueryIODurations','I/O Timings read by queries'],
['getQueryBlks','Blocks by queries'],
['getBgwriterStat','checkpoints_timed'],['getBgwriterStat','checkpoint_write_time'],['getBgwriterStat','buffers_checkpoint'],
['getBlockHitDB','blks_hit_per_sec'],
['getBlockReadDB','blks_read_per_sec'],
['getTupWriteDB','tup_inserted_per_sec'],
['getTupRetFetchDB','tup_returned_per_sec'],
['getTxDB','xact_commit_per_sec'],
['getDeadlocksDB','deadlocks'],
['getAutovacStat','autovacuum_workers'],
['getConnsStat','conns'],
['getLocksStat','All locks'],
['getLog','']];


var compare_dict = [['getCPUStat','HW load -> CPU'],
['getMemUsageStat','HW load -> Memory usage'],
['getDiskUtilStat','HW load -> Disk utilization'],
['getDiskUsageStat','HW load -> Disk usage'],
['getWRQMRRQMStat','HW load -> Read/write req merged per sec'],
['getWRStat','HW load -> Read/Write req per sec'],
['getRSecWSecStat','HW load -> Read/Write MBytes per sec'],
['getAVGRQStat','HW load -> Avg size request'],
['getAVGQUStat','HW load -> Avg queue lenght of requests'],
['getAWaitStat','HW load -> Avg time for I/O requests'],
['getNetworkTrafficStat','HW load -> Network Traffic'],
['getNetworkPacketsStat','HW load -> Network Packets'],
['getNetworkErrorsStat','HW load -> Network Errors'],
['getReadStat','PG load -> Blocks read by tables'],
['getWriteStat','PG load -> Tuples write by tables'],
['getTupStat','PG load -> Scans (seq and index) by tables'], 
['getIndexStat','PG load -> Efficiency index scans by tables'],
['getQueryDurations','PG load -> Query durations'],
['getQueryIODurations','PG load -> I/O Timings read by queries'],
['getQueryBlks','PG load -> Blocks by queries'],
['getBgwriterStat','PG load -> Bgwriter stat'],
['getBlockHitDB','PG load -> Blocks hit by databases'],
['getBlockReadDB','PG load -> Blocks read by databases'],
['getTupWriteDB','PG load -> Tuples write by databases'],
['getTupRetFetchDB','PG load -> Tuples returned/fetched by databases'],
['getTxDB','PG load -> Transactions by databases'],
['getDeadlocksDB','PG load -> Deadlocks'],
['getAutovacStat','PG load -> Autovacuum workers activity'],
['getConnsStat','PG load -> Connections'],
['getLocksStat','PG load -> Locks']];

var time_filter = "<div style=\"width: 100%;text-align: center;\"><div style=\"height:70px;display: inline-block;\">"+
	"<div class=\"pg_stat_console_fonts_on_white \" style=\"float:left;\"> " +
		"<p><b>Time start:</b>"+
			"<input id=\"date_a\" type=\"text\" size=\"30\" class=\"pg_stat_console_control\" style=\"text-align: center;margin-left:10px;width: 140px;\"/>"+
		"</p>"+
	"</div>"+
	"<div class=\"pg_stat_console_fonts_on_white \" style=\"float:left;margin-left:20px;\">"+
		"<p><b>end:</b>"+
			"<input id=\"date_b\" type=\"text\" size=\"30\" class=\"pg_stat_console_control\" style=\"text-align: center;margin-left:10px;width: 140px;\"/>"+
		"</p>"+
	"</div>"+
	"<div id=\"apply_filter_button\" style=\"margin-left:20px;float:left;margin-top:15px;\" class=\"pg_stat_console_fonts pg_stat_console_button\">Apply</div>"+
"</div></div>"+
"<div id=\"graph_space\" style=\"\">"+	
"</div>";

var time_filter_logs = "<div style=\"width: 100%;text-align: center;margin-top:20px;\">"+
	"<div style=\"width: 100%;height:60px;text-align: center;display: inline-block;\">"+
"		<div class=\"pg_stat_console_fonts_on_white \" style=\"display: inline-block;height:60px;\">"+	
	"	<div class=\"pg_stat_console_fonts_on_white \" style=\"float:left;\">"+
"			<p>"+
"				<b>Time start:</b>"+
"				<input id=\"date_a\" type=\"text\" size=\"30\" class=\"pg_stat_console_control\" style=\"text-align: center;margin-left:10px;width: 140px;\">"+
"			</p>"+
"		</div>"+
"		<div class=\"pg_stat_console_fonts_on_white \" style=\"float:left;margin-left:20px;\">"+
"			<p>"+
"				<b>end:</b>"+
"				<input id=\"date_b\" type=\"text\" size=\"30\" class=\"pg_stat_console_control\" style=\"text-align: center;margin-left:10px;width: 140px;\">"+
"			</p>"+
"		</div>"+
"		<div id=\"apply_filter_button\" style=\"margin-left:20px;float:left;margin-top:15px;\" class=\"pg_stat_console_fonts pg_stat_console_button\">"+
"			Apply"+
"		</div>"+
"	</div></div>"+
"	<div style=\"height:50px;display: inline-block;\">"+
"		<div class=\"pg_stat_console_fonts_on_white\" style=\"float:left;\">"+
"			Query lenght [ "+
"			<input class=\"\" id=\"time_len_g\" type=\"radio\" name=\"group\" value=\"great\" checked=\"\">"+
"			great"+
"			<input class=\"\" id=\"time_len_l\" type=\"radio\" name=\"group\" value=\"less\"> less ] than"+
"			<input class=\"pg_stat_console_control\" id=\"time_len_val\" type=\"text\" value=\"0\" style=\"text-align: center;width:50px;\">"+
 "         ms"+
	"	</div>"+
	"</div>"+
"</div>";


var time_filter_compare = "<div style=\"width: 100%;text-align: center;margin-top:20px;\">"+
"	<div style=\"width: 100%;text-align: center;\">"+
"		<div class=\"pg_stat_console_fonts_on_white \">"+
"			First metric "+
"<select class=\"pg_stat_console_control\" style=\"margin-left:10px;margin-right:10px;\" id=\"cmp_param_1\">"+
"</select>"+
"			second metric "+
"<select class=\"pg_stat_console_control\" style=\"margin-left:10px;margin-right:10px;\" id=\"cmp_param_2\">"+
"</select>"+
	"	</div>"+
	"</div>"+
	"<div style=\"height:50px;display: inline-block;\">"+
	"	<div class=\"pg_stat_console_fonts_on_white \" style=\"float:left;\">"+
"			<p>"+
"				<b>Time start:</b>"+
"				<input class=\"pg_stat_console_control\" id=\"date_a\" type=\"text\" size=\"30\" style=\"text-align: center;margin-left:10px;width: 140px;\">"+
"			</p>"+
"		</div>"+
"		<div class=\"pg_stat_console_fonts_on_white \" style=\"float:left;margin-left:10px;\">"+
"			<p>"+
"				<b>end:</b>"+
"				<input class=\"pg_stat_console_control\"id=\"date_b\" type=\"text\" size=\"30\" style=\"text-align: center;margin-left:10px;width: 140px;\">"+
"			</p>"+
"		</div>"+
"		<div id=\"apply_filter_button\" style=\"margin-left:20px;float:left;margin-top:15px;\" class=\"pg_stat_console_fonts pg_stat_console_button\">"+
"			Apply"+
"		</div>"+
"	</div>"+	
"</div>";
	
var time_filter_compare_single_metric = "<div style=\"width: 100%;text-align: center;margin-top:20px;\">"+
  "<table style=\"width:600px;margin-left: auto;margin-right: auto;\" class=\"pg_stat_console_fonts_on_white \">"+
  "<tr>"+
    "<td style=\"width:170px;text-align:right;\"><b>First interval start:</b></td>" +
	"<td style=\"width:170px;text-align:left;\"><input class=\"pg_stat_console_control\" id=\"date_a\" type=\"text\" size=\"30\" style=\"text-align: center;margin-left:10px;width: 140px;\"></td>" +
    "<td><b>end:</b></td>" +
	"<td style=\"width:170px;text-align:left;\"><input class=\"pg_stat_console_control\"id=\"date_b\" type=\"text\" size=\"30\" style=\"text-align: center;width: 140px;\"></td>" +
  "</tr>" +
  "<tr>" +
    "<td style=\"height:50px;width:170px;text-align:right;\" ><b>Second interval start:</b></td>" +
	"<td style=\"width:170px;text-align:left;\"><input class=\"pg_stat_console_control\" id=\"date2_a\" type=\"text\" size=\"30\" style=\"margin-left:10px;text-align: center;width: 140px;\"></td>" +
    "<td><b>end:</b></td>" +
	"<td style=\"width:170px;text-align:left;\"><input class=\"pg_stat_console_control\"id=\"date2_b\" type=\"text\" size=\"30\" style=\"text-align: center;width: 140px;\"></td>" +
  "</tr>" +
"</table>" +
"<table style=\"width:600px;margin-top:2px;margin-left: auto;margin-right: auto;\" class=\"pg_stat_console_fonts_on_white \">"+
  "<tr>" +
	"<td style=\"width:70px;text-align:right;\">Metric</td>" +
    "<td style=\"text-align:left;\"><select class=\"pg_stat_console_control\" style=\"margin-left:10px;margin-right:10px;\" id=\"cmp_param\"></select></td>" +
	"<td style=\"text-align:left;width:70px;\"><div id=\"apply_filter_button\" style=\"\" class=\"pg_stat_console_fonts pg_stat_console_button\">Apply</div></td>" +
   "</tr>" + 
"</table></div>";


var div_no_data = "<div style=\"text-align: center;margin-top:10px;\">no data</div>";
var div_query_canceled = "<div style=\"text-align: center;margin-top:10px;\">Query canceled!</div>";

var sub_space = "<div id=\"sub_space\" class=\"pg_stat_console_fonts_on_white_na\" style=\"word-break:break-all;word-wrap:break-word;width:100%;\"></div>";
var sub_space_2 = "<div id=\"sub_space_2\" class=\"pg_stat_console_fonts_on_white_na\" style=\"word-break:break-all;word-wrap:break-word;width:100%;\"></div>";
	
Date.daysBetween = function( date_a, date_b ) {
  var one_day=1000*60*60*24;
  var date_a_ms = date_a.getTime();
  var date_b_ms = date_b.getTime();
  var difference_ms = date_b_ms - date_a_ms;
  return Math.round(difference_ms/one_day); 
}
	
function all_xhr_abort()
{
	for (var i = 0; i < current_xhr.length; i++)
	{
		if( typeof current_xhr[i] !== 'undefined' )
			current_xhr[i].abort();
	}
	current_xhr = [];
	load_process = [];
}
	
function show_error( textStatus, errorThrown, descr )
{
	var descr_v;
	if (descr.length >= 1500)
		descr_v = descr.substring(0, 1500) + "...";
	else
		descr_v = descr;
	
	descr_v = descr_v.replace(/ /g, '&nbsp;');
	descr_v = descr_v.replace(/(?:\r\n|\r|\n)/g, '<br />');
	descr_v = descr_v.replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;');
	
	//var $content_help = '<p>Status: ' + textStatus + '</p><p>Error: ' + errorThrown + '</p><div align="left" style="font-size: 8pt"><p>' + descr_v + '</p></div>';
	var $content_help = '<p>Error: ' + errorThrown + '</p><div align="left" style="font-size: 8pt"><p>' + descr_v + '</p></div>';
	new $.flavr({ 
		title   : 'Error',
		content : $content_help, 
		animateEntrance  : 'fadeInDown',
		animateClosing    : 'fadeOutDown',
		html    : true,
		closeOverlay : true,
		closeEsc     : true,
		onClose     : function(){    
			//to do call_login_dialog();
		},											
	});	
}
	
function hide_all_submenu()
{
	$('#sub_menu_1').fadeOut( 250 );
	$('#sub_menu_2').fadeOut( 250 );
	$('#sub_menu_2_2').fadeOut( 250 );	
	$('#sub_menu_3').fadeOut( 250 );
	$('#sub_menu_4').fadeOut( 250 );	
	$('#sub_menu_5').fadeOut( 250 );
}	
	

function show_common_div()
{
	$('#common_content').css('visibility', 'visible');
}

function hide_common_div()
{
	$('#common_content').css('visibility', 'hidden');
	hide_all_submenu();
}


function notice( msg, func )
{
	var $content_help = msg;
	new $.flavr({ 
		content : $content_help, 
		animateEntrance  : 'fadeIn',
		animateClosing    : 'fadeOut',
		buttons : {},
		html    : true,
		autoclose: true, timeout: 2500,
		onClose     : function(){    
			if( typeof func !== 'undefined' )
				func();
		},											
	});
}

function dlg_ok( caption, msg, func )
{
	var $content_help = msg;
	new $.flavr({ 
		title   : caption,
		content : $content_help, 
		animateEntrance  : 'fadeInDown',
		animateClosing    : 'fadeOutDown',
		html    : true,
		closeOverlay : true,
		closeEsc     : true,
		onClose     : function(){    
			if( typeof func !== 'undefined' )
				func();
		},			
	});
}

function check_dates_interval( date_a_v, date_b_v, days_num )
{
	var res = true;
	if( Date.daysBetween( new Date(date_a_v), new Date(date_b_v) ) >= days_num )
	{
		dlg_ok( "Error", "<p>Please enter interval less than " + days_num.toString() + " days!</p>" );
		res = false;
	}
	return res;
}

function show_progress()
{
	if( progress_hidden == true )
	{
		$( "#progress_bar" ).fadeIn( "slow" );
		$('#progress_bar').append("<div class=\"pg_stat_console_loader\"></div>");
		progress_visisble = true;
		progress_hidden = false;
	}
}

function hide_progress()
{
	if( progress_visisble == true )
	{
		$( "#progress_bar" ).fadeOut( "slow", function() { $('#progress_bar').empty(); } );
		progress_visisble = false;
		progress_hidden = true;	
	}
}

function progress_notice( msg )
{
	load_process_closed = false;

	var $content_help = msg;
	new $.flavr({ 
		content : $content_help, 
		animateEntrance  : 'fadeIn',
		buttons : {
			cancel : { text: 'Cancel query', action: function( $cont ){
					all_xhr_abort();
					close_flavr_container();
					return false;
			}}		

		},
		html    : true										
	});
}

function close_flavr_container()
{
	$( ".flavr-container .flavr-title" ).each(function( index ) {
		if( $(this).text().length == 0 )
			$(this).parent().parent().parent().parent().fadeOut( "slow", function() {
				$(this).parent().parent().parent().parent().remove();
			});			
	});
}

function call_login_dialog()
{
	var help_msg = "";

	$.ajax({ url: '/getCustomParam',
			type: 'post',
			data: JSON.stringify( { param_name: 'application_title' } ),
			success: function(data) {
				title_val = data["result"] ;
				$.ajax({ url: '/getCustomParam',
						type: 'post',
						data: JSON.stringify( { param_name: 'help_msg' } ),
						success: function(data) {
							help_msg = data["result"];
							show_login_dialog(title_val, help_msg);	
						},
						error: function(XMLHttpRequest, textStatus, errorThrown) {
						}
				});	
			},
			error: function(XMLHttpRequest, textStatus, errorThrown) {
			}
	});
}

function get_current_user_type()
{
	$.ajax({ url: '/getUserType',
			type: 'post',
			data: JSON.stringify( { user_name: user_name_val, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
			success: function(data) {
				current_user_type = data;
				/*
				if( current_user_type !== "admin" )
					$("#button_show_status").hide();
				else
					$("#button_show_status").show();
				*/
			},
			error: function(XMLHttpRequest, textStatus, errorThrown) {
			}
	});		
}

function get_current_status()
{
	if( current_node_name == "null" || current_node_name == null )
	{
		$("#status_panel").fadeOut( 250 );
	} else
	{
		$("#status_panel").fadeIn( 250 );
		$.ajax({ url: '/getPgStatConsoleStatus',
				type: 'post',
				data: JSON.stringify( {node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data')} ),
				success: function(data) {
					if( data )
					{
						$("#status_info").empty();
						$("#status_info").append( "<div>Node status OK</div>" );
					}
					else
					{
						$("#status_info").empty();
						$("#status_info").append( "<div>Node status <b>Fail</b></div>" );
					}
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
				}
		});
	}	
}

function get_current_node_info()
{
	var node_classes = [ 'node_class_psc_tbls_stat', 'node_class_psc_os_stat', 'node_class_psc_snapshots', 'node_class_pg_stat_monitor' ];
	if( !( current_node_name == "null" || current_node_name == null ) )
	{
		$.ajax({ url: '/getPgStatConsoleNodeInfo',
				type: 'post',
				data: JSON.stringify( {node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data')} ),
				success: function(data) {
					if( data )
					{
						current_node_info = [];
						for (var i = 0; i < data.length; i++)
						{
							if( 'psc_tbls_stat' == data[i] ) current_node_info.push('node_class_psc_tbls_stat');
							if( 'psc_os_stat' == data[i] ) current_node_info.push('node_class_psc_os_stat');
							if( 'psc_snapshots' == data[i] ) current_node_info.push('node_class_psc_snapshots');
							if( 'pg_stat_monitor' == data[i] ) current_node_info.push('node_class_pg_stat_monitor');
						}

						for (var i = 0; i < node_classes.length; i++)
							if( current_node_info.includes(node_classes[i]) == false )
								$('.' + node_classes[i]).fadeOut( 250 );
						
						for (var i = 0; i < node_classes.length; i++)
							if( current_node_info.includes(node_classes[i]) )
								$('.' + node_classes[i]).fadeIn( 250 );
					}
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
				}
		});
	}
}

function get_current_db_status()
{
	if( current_node_name != "null" && current_node_name != null && current_node_info.includes("node_class_pg_stat_monitor") )
	{
		$.ajax({ url: '/getMaintenanceStatus',
				type: 'post',
				data: JSON.stringify( {node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data')} ),
				success: function(data) {
					if( data == true || data == 'true' )
					{
						$('#db_status_panel').css('visibility', 'visible');
						$("#db_status_panel" ).fadeIn( "slow" );
					}
					else if( data == false || data == 'false' )
					{
						$('#db_status_panel').css('visibility', 'hidden');
						$("#db_status_panel" ).fadeOut( "slow" );
					}
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
				}
		});	
	}
}
	
function getRandomInt(min, max)
{
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function success_login( login_name )
{
	show_common_div();
	$('#user_name_div').text( "Hello, " + login_name );
	get_uptime();
	user_name_val = login_name;
	get_current_user_type();
	get_current_status();
	get_current_db_status();
	init_settings();
}

function set_user_auth_data( param_p, value_p )
{
	var user_auth_data = [];
	if(localStorage.getItem('user_auth_data') != null)
		user_auth_data = JSON.parse(localStorage.getItem('user_auth_data'));
	
	var param_exists = false;
	for (var i = 0; i < user_auth_data.length; i++)
		if( user_auth_data[i].param == param_p )
		{
			param_exists = true;
			user_auth_data[i].value = value_p;
		}

	if(param_exists== false)
		user_auth_data.push( { param:param_p, value:value_p } );

	localStorage.setItem('user_auth_data', JSON.stringify(user_auth_data));
}

function get_user_auth_data( param_p )
{
	if(localStorage.getItem('user_auth_data') != null)
	{
		var user_auth_data = JSON.parse(localStorage.getItem('user_auth_data'));
		for (var i = 0; i < user_auth_data.length; i++)	
			if( user_auth_data[i].param == param_p )
				return user_auth_data[i].value;
	}
	return undefined;
}

function show_login_dialog(title_val, help_msg)
{
		var $content = 
			'<img height="80" width="345" src="img/logo.png" style=""/>'+
			'<p>put your credentials</p>'+
			'<form>' +
			'   <div class="form-row">'+               
			'   </div>'+
			'</form>' +
			'<form class="flavr-form form-html">' +
			'   <div class="form-row">' +
			'       <input onkeydown="if (event.keyCode == 13) $(\'a[rel=btn-log_in]\').click();" id="login_fld" type="text" name="login_fld" ' +
			'       placeholder="Login" />' +
			'   </div>' +
			'   <div class="form-row">' +
			'       <input onkeydown="if (event.keyCode == 13) $(\'a[rel=btn-log_in]\').click();" id="passw_fld" type="password" name="passw_fld" ' +
			'       placeholder="Password" />' +
			'   </div>' +
			'<p></p>'
			'</form>';                        
		
		new $.flavr({
			title	: 'Welcome to ' + title_val + '!',
			content : $content,
			animateClosing: 'flipOutX',
			buttons : {
					log_in : { text: 'OK', action: function( $cont ){

						if( $('#login_fld').val().length < 1 || $('#passw_fld').val().length < 1 )
						{
							new $.flavr({ 
								title   : 'Error',
								content : 'Please enter all fields!', 
								animateEntrance  : 'fadeInDown',
								animateClosing    : 'fadeOutDown',
								html    : false,
								closeOverlay : true,
								closeEsc     : true		
							});
						    return false;
						} else { 
						
						return_val = false;
						$.ajax({ url: '/login',
								type: 'post',
								data: JSON.stringify({ login: $('#login_fld').val(), password: $('#passw_fld').val() }),
								success: function(data) {
									if( data["result"] === 'ok' )
									{
										var msg_num = getRandomInt(0, 7);
										var welcome_msgs = [ '<p>Time is money</p>',
												'<p>Better late than never</p>',
												'<p>You\'re here! The day just got better.</p>',
												'<p>If you snooze, you lose</p>',
												'<p>There\'s no smoke without fire</p>',
												'<p>Strike while the iron is hot</p>',
												'<p>Many hands make light work</p>',
												'<p>Where there\'s a will, there\'s a way</p>'];

										var user_name = $('#login_fld').val();
	
										set_user_auth_data( "user_hash",  data["user_hash"] );
										set_user_auth_data( "user_name",  user_name );

												
										notice( '<div style="font-size:25px;">' + welcome_msgs[ msg_num ] + '</div>', function()
										{
											success_login( user_name );
										});

									} else {
										var $content_help = '<p>Wrong password!</p>';
										new $.flavr({ 
											title   : 'Error',
											content : $content_help, 
											animateEntrance  : 'fadeInDown',
											animateClosing    : 'fadeOutDown',
											html    : true,
											closeOverlay : true,
											closeEsc     : true,
											onClose     : function(){    
												call_login_dialog();
											}											
										});
									}},
								error: function(XMLHttpRequest, textStatus, errorThrown) {
										var $content_help = '<p>Status: ' + textStatus + '</p><p>Error: ' + errorThrown + '</p>';
										new $.flavr({ 
											title   : 'Error',
											content : $content_help, 
											animateEntrance  : 'fadeInDown',
											animateClosing    : 'fadeOutDown',
											html    : true,
											closeOverlay : true,
											closeEsc     : true,
											onClose     : function(){    
												call_login_dialog();
											},											
										});
									}								
						});	
							
							return true;
						}	
					}},
					help : { text: 'help', action: function( $cont ){
							var $content_help = help_msg;
							new $.flavr({ 
								title   : 'Help',
								content : $content_help, 
								animateEntrance  : 'fadeInDown',
								animateClosing    : 'fadeOutDown',
								html    : true,
								closeOverlay : true,
								closeEsc     : true								
							});
							return false;
					}}					
					
			},
			onShow      : function(){
				$( "#login_fld" ).focus();
			},	
			onClose     : function(){    
			},
			//closeOverlay : true,
			//closeEsc     : true
		});
}

function make_dates_interval_str( last_hours )
{
	var date_a = new Date();
	date_a.setTime( date_a.getTime() - date_a.getTimezoneOffset()*60*1000 );
	date_a.setDate(date_a.getDate());
	date_a.setHours(date_a.getHours() - last_hours );
	
	var date_a0 = date_a.toISOString().slice(0, 19).replace('T', ' ');
		
	var date_b = new Date();
	date_b.setTime( date_b.getTime() - date_b.getTimezoneOffset()*60*1000 );
	date_b.setDate(date_b.getDate());
	date_b.setHours(date_b.getHours());
	var date_b0 = date_b.toISOString().slice(0, 19).replace('T', ' ');
	return [ date_a0, date_b0 ]
}

function date_time_objs( last_hours, date_a_id_name, date_b_id_name, step_back_in_hours )
{
	var step_back = 0;
	if( typeof step_back_in_hours !== 'undefined' )
		step_back = step_back_in_hours;
		
	var date_a = new Date();
	date_a.setTime( date_a.getTime() - date_a.getTimezoneOffset()*60*1000 );
	date_a.setDate(date_a.getDate());
	date_a.setHours(date_a.getHours() - last_hours - step_back );
	
	var date_a0 = date_a.toISOString().slice(0, 19).replace('T', ' ');
		
	var date_b = new Date();
	date_b.setTime( date_b.getTime() - date_b.getTimezoneOffset()*60*1000 );
	date_b.setDate(date_b.getDate());
	date_b.setHours(date_b.getHours() - step_back );
	var date_b0 = date_b.toISOString().slice(0, 19).replace('T', ' ');


	var date_time_params = {
		autoClose: false,
		format: 'YYYY-MM-DD HH:mm:ss',
		separator: ' to ',
		language: 'en',
		startOfWeek: 'monday',
		getValue: function()
		{
			if ($('#'+date_a_id_name).val() && $('#'+date_b_id_name).val() )
				return $('#'+date_a_id_name).val() + ' to ' + $('#'+date_b_id_name).val();
			else
				return '';
		},
		setValue: function(s,s1,s2)
		{
			$('#'+date_a_id_name).val(s1);
			$('#'+date_b_id_name).val(s2);
		},
		//startDate: date_a0,
		//endDate: date_b0,
		time: {
			enabled: true
		},
		minDays: 0,
		maxDays: 15,
		showShortcuts: false,
		shortcuts:
		{
			//'prev-days': [1,3,5,7],
			//'next-days': [3,5,7],
			//'prev' : ['week','month','year'],
			//'next' : ['week','month','year']
		},
		customShortcuts : [],
		inline:false,
		container:'body',
		alwaysOpen:false,
		singleDate:false,
		lookBehind: false,
		batchMode: false,
		//duration: 200,
		stickyMonths: false,
		dayDivAttrs: [],
		dayTdAttrs: [],
		applyBtnClass: '',
		singleMonth: 'auto',
		hoveringTooltip: function(days, startTime, hoveringTime)
		{
			return days > 1 ? days + ' ' + 'days' : '';
		},
		showTopbar: true,
		swapTime: false,
		selectForward: false,
		selectBackward: false,
		showWeekNumbers: false,
		getWeekNumber: function(date) //date will be the first day of a week
		{
			return moment(date).format('w');
		}
	};
	return [date_a0,date_b0,date_time_params];
}	

function set_date_time_filter( last_hours )
{
	if( demo_dt_a !== "" && demo_dt_a !== 'undefined param name' &&
		demo_dt_b !== "" && demo_dt_b !== 'undefined param name' )
	{
		init_work_space();
		$( "#work_space" ).append( time_filter );
		$('input[id^="date"]').unbind( "click" );
		$('input[id^="date"]').prop('disabled', true);
		
		$("#date_a").val(demo_dt_a);
		$("#date_b").val(demo_dt_b);
	}
	else
	{
		var date_time_objs_v = date_time_objs( last_hours, 'date_a', 'date_b' );
		init_work_space();
		$( "#work_space" ).append( time_filter );
					
		$('input[id^="date"]').unbind( "click" );

		$('.date-picker-wrapper').remove();
		$('#date_a').dateRangePicker(date_time_objs_v[2]);
		$('#date_b').dateRangePicker(date_time_objs_v[2]);		
		$("#date_a").val(date_time_objs_v[0]);
		$("#date_b").val(date_time_objs_v[1]);
	}
}

function set_date_time_filter_compare_params( last_hours )
{	
	if( demo_dt_a !== "" && demo_dt_a !== 'undefined param name' &&
		demo_dt_b !== "" && demo_dt_b !== 'undefined param name' )
	{
		init_work_space();
		$( "#work_space" ).append( time_filter_compare );
		$('input[id^="date"]').unbind( "click" );
		$('input[id^="date"]').prop('disabled', true);
		
		$('.date-picker-wrapper').remove();
		
		for (var i = 0; i < compare_dict.length; i++)	
			$('select[id^="cmp_param_"]').append($("<option/>", {
				value: compare_dict[i][0],
				text: compare_dict[i][1]
			}));
		
		$("#date_a").val(demo_dt_a);
		$("#date_b").val(demo_dt_b);
	}
	else
	{
		var date_time_objs_v = date_time_objs( last_hours, 'date_a', 'date_b' );
		
		init_work_space();
		$( "#work_space" ).append( time_filter_compare );
		$('input[id^="date"]').unbind( "click" );
		$('.date-picker-wrapper').remove();
		
		for (var i = 0; i < compare_dict.length; i++)	
			$('select[id^="cmp_param_"]').append($("<option/>", {
				value: compare_dict[i][0],
				text: compare_dict[i][1]
			}));
		
		$('#date_a').dateRangePicker(date_time_objs_v[2]);
		$('#date_b').dateRangePicker(date_time_objs_v[2]);		
		$("#date_a").val(date_time_objs_v[0]);
		$("#date_b").val(date_time_objs_v[1]);
	}
}	

function set_date_time_filter_compare_single_params( last_hours )
{
	if( demo_dt_a !== "" && demo_dt_a !== 'undefined param name' &&
		demo_dt_b !== "" && demo_dt_b !== 'undefined param name' )
	{
		init_work_space();
		$( "#work_space" ).append( time_filter_compare_single_metric );

		$('input[id^="date"]').unbind( "click" );
		$('input[id^="date"]').prop('disabled', true);
		
		$('.date-picker-wrapper').remove();
		
		for (var i = 0; i < compare_dict.length; i++)
			$('select[id^="cmp_param"]').append($("<option/>", {
				value: compare_dict[i][0],
				text: compare_dict[i][1]
			}));
		
		$("#date_a").val(demo_dt_a);
		$("#date_b").val(demo_dt_b);
		
		var date2_a = new Date( demo_dt_a );
		var date2_b = new Date( demo_dt_b );
		
		date2_a.setHours(date2_a.getHours()-4);
		date2_b.setHours(date2_b.getHours()-4);
		
		$("#date2_a").val(date2_a.toISOString().slice(0, 19).replace('T', ' '));
		$("#date2_b").val(date2_b.toISOString().slice(0, 19).replace('T', ' '));		
	}
	else
	{
		var date_time_objs_v = date_time_objs( last_hours, 'date_a', 'date_b' );
		var date_time_objs2_v = date_time_objs( last_hours, 'date2_a', 'date2_b', 24 );
		
		init_work_space();
		$( "#work_space" ).append( time_filter_compare_single_metric );	
		$('input[id^="date"]').unbind( "click" );
		$('.date-picker-wrapper').remove();
		
		for (var i = 0; i < compare_dict.length; i++)
			$('select[id^="cmp_param"]').append($("<option/>", {
				value: compare_dict[i][0],
				text: compare_dict[i][1]
			}));		
		
		$('#date_a').dateRangePicker(date_time_objs_v[2]);
		$('#date_b').dateRangePicker(date_time_objs_v[2]);		
		$("#date_a").val(date_time_objs_v[0]);
		$("#date_b").val(date_time_objs_v[1]);
		
		$('#date2_a').dateRangePicker(date_time_objs2_v[2]);
		$('#date2_b').dateRangePicker(date_time_objs2_v[2]);		
		$("#date2_a").val(date_time_objs2_v[0]);
		$("#date2_b").val(date_time_objs2_v[1]);	
	}
}		

function set_date_time_log_filter(last_hours)
{
	if( demo_dt_a !== "" && demo_dt_a !== 'undefined param name' &&
		demo_dt_b !== "" && demo_dt_b !== 'undefined param name' )
	{
		init_work_space();
		$( "#work_space" ).append( time_filter_logs );
		$('input[id^="date"]').unbind( "click" );
		$('input[id^="date"]').prop('disabled', true);
		
		$("#date_a").val(demo_dt_a);
		$("#date_b").val(demo_dt_b);
	}
	else
	{
		var date_time_objs_v = date_time_objs( last_hours, 'date_a', 'date_b' );

		init_work_space();
		$( "#work_space" ).append( time_filter_logs );	

		$('input[id^="date"]').unbind( "click" );

		$('.date-picker-wrapper').remove();
		$('#date_a').dateRangePicker(date_time_objs_v[2]);
		$('#date_b').dateRangePicker(date_time_objs_v[2]);			
		$("#date_a").val(date_time_objs_v[0]);
		$("#date_b").val(date_time_objs_v[1]);
	}
}	

function set_old_conn_filter()
{
	$( "#work_space" ).empty();
	$( "#work_space" ).append( "<div>"+
		"	<div style=\"width: 100%; margin: 0 auto;height:30px;text-align: center; margin-top:20px;margin-bottom:20px;\">"+
		"		<div class=\"pg_stat_console_fonts_on_white\" style=\'display:inline-block;\'>"+
		"			Connection age great than"+
		"			<input id=\"conn_age\" type=\"text\" value=\"0\" class=\"pg_stat_console_control\" style=\"margin-left:5px;margin-right:5px;text-align:center;width:50px;\">"+
		 "         minutes"+
			"	</div>"+
		"		<div id=\"apply_filter_button\" style=\"margin-left:20px;display:inline-block;\" class=\"pg_stat_console_fonts pg_stat_console_button\">"+
		"			Apply"+
		"		</div>"+				
			"</div>"+
		"</div>" );
	
	$("#conn_age").val("60");
}

function get_uptime()
{
	if( current_node_name == "null" || current_node_name == null )
	{
		$("#uptime").fadeOut( 250 );
	} else
		if( current_node_info.includes("node_class_pg_stat_monitor") )
			$.ajax({ url: '/getUptime',
					type: 'post',
					data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
					success: function(data) {
						if( data == 'pg_stat_monitor not allowed')
							$("#uptime").fadeOut( 250 );
						else
						{
							$("#uptime").fadeIn( 250 );
							$('#uptime').text( "Uptime " + data );
						}
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							if( textStatus !== "abort" ) show_error( textStatus, errorThrown, XMLHttpRequest.responseText );
						}
			});
}	

function get_refresh_interval()
{
	$.ajax({ url: '/getRefreshInterval',
			type: 'get',
			success: function(data) {
				if( parseInt( data ) >= 3 && parseInt( data ) < 10000 )
					refresh_interval = parseInt( data );
			},
			error: function(XMLHttpRequest, textStatus, errorThrown) {
					if( textStatus !== "abort" ) show_error( textStatus, errorThrown, XMLHttpRequest.responseText );
				}
	});
}	

function show_autorefresh()
{
	$( "#button_refresh" ).fadeOut( "slow" , function(){
		$( "#auto_refresh_div" ).fadeIn( "slow", function(){
			$( "#button_refresh" ).fadeIn( "slow" );
		});		
	});
}

function hide_autorefresh()
{
	$( "#button_refresh" ).fadeOut( "slow" , function(){
		$( "#auto_refresh_div" ).fadeOut( "slow", function(){
			$( "#button_refresh" ).fadeIn( "slow" );
		});		
	});
}


function scroll_page_to_table_num( num )
{
	$('#main_work_space').animate({
			scrollTop: $( $(".scrollable_obj")[ num - 1 ] ).offset().top + document.getElementById('main_work_space').scrollTop - 50
		}, 500);
}

function reset_up_down_buttons()
{
	table_num_viewed = 1;
	
	if( selected_menu_elem.name == 'sub_menu_start_dashboard' ) 
	{
		hide_up_down_buttons();
	} else
	{
		if( $(".scrollable_obj").length >= 2 )
		{
			$(".pg_stat_console_step_down").fadeIn(800, function(){});
			$(".pg_stat_console_step_up").fadeOut(800, function(){});
		} else
		{
			$(".pg_stat_console_step_up").fadeOut(800, function(){});
			$(".pg_stat_console_step_down").fadeOut(800, function(){});		
		}
	}
}

function hide_up_down_buttons()
{
	$(".pg_stat_console_step_down").fadeOut(800, function(){ $(".pg_stat_console_step_down").css( 'display', 'none' )});
	$(".pg_stat_console_step_up").fadeOut(800, function(){ $(".pg_stat_console_step_up").css( 'display', 'none' )});
}

function show_up_down_buttons()
{
		//$(".pg_stat_console_step_down").css( 'display', 'inline' );
		//$(".pg_stat_console_step_up").css( 'display', 'inline' );
		
		if( $(".scrollable_obj").length >= 2 )
		{
			$(".pg_stat_console_step_down").fadeIn(800, function(){});
			$(".pg_stat_console_step_up").fadeOut(800, function(){});
		} else
		{
			$(".pg_stat_console_step_up").fadeOut(800, function(){});
			$(".pg_stat_console_step_down").fadeOut(800, function(){});		
		}
}

function init_settings()
{
	if( localStorage.getItem('user_config') == null )
		$("#button_settings").click();
	else
		if(( current_node_name != "null") && ( current_node_name != null ))
			$( "#sub_menu_start_dashboard" ).click();
		else
			$("#button_settings").click();

	$(".pg_stat_console_left").css({"margin-left":"-100px"}).fadeIn( 250 ).delay(1000).animate(
			{"margin-left":"20px"}, {duration: 'slow', easing:"easeOutBounce"}
		).delay(2300).animate(
			{ "margin-left":"-100px" }, {duration: 'slow',easing: 'easeOutQuart'}
		);
	get_current_node_info();
}

jQuery.fn.sortElements = (function(){
 
    var sort = [].sort;
 
    return function(comparator, getSortable) {
 
        getSortable = getSortable || function(){return this;};
 
        var placements = this.map(function(){
 
            var sortElement = getSortable.call(this),
                parentNode = sortElement.parentNode,
                nextSibling = parentNode.insertBefore(
                    document.createTextNode(''),
                    sortElement.nextSibling
                );
 
            return function() {
 
                if (parentNode === this) {
                    throw new Error(
                        "You can't sort elements if any one is a descendant of another."
                    );
                }
 
                // Insert before flag:
                parentNode.insertBefore(this, nextSibling);
                // Remove flag:
                parentNode.removeChild(nextSibling);
 
            };
 
        });
 
        return sort.call(this, comparator).each(function(i){
            placements[i].call(getSortable.call(this));
        });
 
    };
 
})();

function sort_charts_by_dict( dict, order )
{
	$('div[id^="chartContainer_"]').sortElements(function(a, b){
		var a_name = $(a).attr("chart-name");
		var b_name = $(b).attr("chart-name");
		var a_index = -1;
		var b_index = -1;
		
		function get_index_in_user_order(method)
		{
			var res = -1;
			for (var i = 0; i < order.length; i++)	
				if( order[i][0] == method )
					res = i;
			return res;
		}
		
		for (var i = 0; i < dict.length; i++) {
			if( dict[i][1] !== "" )
			{
				if( a_name.indexOf( dict[i][1] ) > -1 )
					a_index = get_index_in_user_order(dict[i][0]);
				if( b_name.indexOf( dict[i][1] ) > -1 )
					b_index = get_index_in_user_order(dict[i][0]);
			} else
			{
				if((a_index == -1)&&(b_index == -1))
				{
					a_index = 0;
					b_index = 100;
				}
			}
		}	
		return a_index > b_index ? 1 : -1;
	});
}

function redraw_dashboard()
{
	$('div[id^="chartContainer_"]').width('50%');
	$('div[id^="chartContainer_"]').css('float','left');
	for (var i = 0; i < all_charts_on_page.length; i++) {	
		if("legend" in all_charts_on_page[i].options) {
			all_charts_on_page[i].options.legend.fontSize = 12;
		}
	}	
	for (var i = 0; i < all_charts_on_page.length; i++) {	
		all_charts_on_page[i].render();
	}	

	sort_charts_by_dict( dashboard_dict, user_dashboard );
	
	reset_up_down_buttons();
}

function init_work_space()
{
	all_charts_on_page = [];
	$( "#menu_3d_cover" ).css('height','100%');
	$( "#work_space" ).empty();
	hide_all_submenu();	
}

function apply_sort_tables()
{
	$('.header').unbind( "click" );
	$('.tablesorter').each(function() {
		if( $( "tr", this ).length > 1 )
			$(this).tablesorter();
	});	
	reset_up_down_buttons();
	
}

function graph_post( method, date_a_v, date_b_v, func )
{
	if( check_dates_interval( date_a_v, date_b_v, 5 ) )
	{
		load_process.push( true );
		current_xhr.push( $.ajax({ url: '/' + method,
					type: 'post',
					data: JSON.stringify( { date_a: date_a_v, date_b: date_b_v, node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
					success: function(data) {
						eval(data);
						load_process.pop();
						reset_up_down_buttons();
						if( typeof func !== 'undefined' )
							func();						
					},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						load_process.pop();
						if( textStatus !== "abort" ) 
							show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
						else
						{
							$( "#sub_space" ).empty();
							$( "#sub_space" ).append( div_query_canceled );
						}
					}
			}));
	}
}

function set_nodes()
{
	var nodes = [];
	var nodes_res = [];
	if( localStorage.getItem('user_config') != null )
	{
		var params_obj = JSON.parse(localStorage.getItem('user_config'));
		for (var i = 0; i < params_obj.length; i++)
			nodes.push( params_obj[i].node_name );

		function unique(value, index, self) { 
			return self.indexOf(value) === index;
		}	
		nodes_res = nodes.filter( unique );
	}
	
	$('#nodes_select').empty();
	for (var i = 0; i < nodes_res.length; i++)
		$('#nodes_select').append($("<option></option>").attr("value",nodes_res[i]).text(nodes_res[i]));
	
	if( get_user_auth_data( "selected_node_name") != undefined )
	{
		current_node_name = get_user_auth_data( "selected_node_name");
		$( "#nodes_select" ).val(current_node_name);
	} else
	{
		current_node_name = $( "#nodes_select" ).val();
		set_user_auth_data( "selected_node_name", current_node_name );
	}
	
	if( nodes_res.length == 0 )
	{
		$('#nodes_select').append($("<option></option>").attr("value","null").text("Please select db or device..."));
		$("#uptime").fadeOut( 250 );
		$("#status_panel").fadeOut( 250 );
		$("#menu_elems").fadeOut( 250 );
	} else
	{
		$("#uptime").fadeIn( 250 );
		$("#status_panel").fadeIn( 250 );
		$("#menu_elems").fadeIn( 250 );		
	}

}

function click_on_check_boxes_in_settings()
{
	//<input class="conf_param" type="checkbox" param_name="vda" node_name="test node" param_type="device_in_report" value="a1">
	//<input class="conf_param" type="checkbox" param_name="test_dev" node_name="test node" param_type="db_in_report" value="a1">
	
	function set_user_config()
	{
		var params = [];
		$(".conf_param").each(function() {
			if( $(this).is(':checked') )
				params.push( { "param_name": $(this).attr("param_name"), "node_name": $(this).attr("node_name"), "param_type": $(this).attr("param_type") } );
		});
		localStorage.setItem('user_config', JSON.stringify( params ));
		set_nodes();
	}
	
	$(".conf_param").unbind( "click" );
	$(".conf_param").each(function() {
		$(this).click( function(){
			set_user_config();				
		});
	});
	
	function check_param(params_obj, param_name_p, param_type_p, node_name_p )
	{
		for (var i = 0; i < params_obj.length; i++)
		{
			if( params_obj[i].param_name == param_name_p && 
				params_obj[i].param_type == param_type_p && 
				params_obj[i].node_name == node_name_p )
				return true;
				
		}
		return false;
	}
	
	if( localStorage.getItem('user_config') != null )
	{
		var params_obj = JSON.parse(localStorage.getItem('user_config'));
		$(".conf_param").each(function() {

			if( check_param( params_obj, $(this).attr("param_name"), $(this).attr("param_type"), $(this).attr("node_name") ) )
				$(this).prop('checked', true)	
		});
	}
	
	//<div  class="select_all" node_name="test node">Select all</div>
	$('.select_all, .deselect_all').unbind( "click" );
	$('.select_all').each(function() {
		$(this).click( function(){
			var curr_node_name = $(this).attr("node_name");
			
			$(".conf_param").each(function() {
				if( $(this).attr("node_name") == curr_node_name )
					$(this).prop('checked', true);
			});
			set_user_config();	
		});
	});
	$('.deselect_all').each(function() {
		$(this).click( function(){
			var curr_node_name = $(this).attr("node_name");
			
			$(".conf_param").each(function() {
				if( $(this).attr("node_name") == curr_node_name )
					$(this).prop('checked', false);
			});
			set_user_config();	
		});
	});	
}

function check_user_name_hash()
{
	if( get_user_auth_data( "user_name") !== undefined && get_user_auth_data( "user_hash") !== undefined )
	{
		$.ajax({ url: '/check_user_hash',
				type: 'post',
				data: JSON.stringify({ user_name: get_user_auth_data( "user_name"), user_hash: get_user_auth_data( "user_hash") }),
				success: function(data) {

					if( data["result"] === 'ok' )
					{				
						success_login( get_user_auth_data( "user_name") );
					} else
					{
						call_login_dialog();
					}
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) show_error( textStatus, errorThrown, XMLHttpRequest.responseText );
					}
		});									
	
		
	} else
	{
		call_login_dialog();
	}	
}

function set_all_click_events()
{
	$(".pg_stat_console_step_up").click(function(){
	    if( $(".scrollable_obj").length >= 2 )
		{		
			if( table_num_viewed >= 2 )
			{
				table_num_viewed -= 1;
				scroll_page_to_table_num( table_num_viewed );
				if( table_num_viewed != $(".scrollable_obj").length )
					$(".pg_stat_console_step_down").fadeIn(800, function(){});					
			}		
			if( table_num_viewed == 1 )
			{
				$(".pg_stat_console_step_up").fadeOut(800, function(){});	
				$(".pg_stat_console_step_down").fadeIn(800, function(){});	
			}
			else
				$(".pg_stat_console_step_up").fadeIn(800, function(){});
		}
	});	
	
	$(".pg_stat_console_step_down").click(function(){
	    if( $(".scrollable_obj").length >= 2 )
		{		
			if( table_num_viewed + 1 <= $(".scrollable_obj").length )
			{
				table_num_viewed += 1;
				scroll_page_to_table_num( table_num_viewed );
				if( table_num_viewed != 1 )
					$(".pg_stat_console_step_up").fadeIn(800, function(){});				
			}
			if( table_num_viewed == $(".scrollable_obj").length )
			{
				$(".pg_stat_console_step_down").fadeOut(800, function(){});
				$(".pg_stat_console_step_up").fadeIn(800, function(){});
			}
			else
				$(".pg_stat_console_step_down").fadeIn(800, function(){});		
		}
	});
	
	var e = $(".pg_stat_console_goto_top");
	e.click(function(){
		reset_up_down_buttons();
		$("#main_work_space").animate({ scrollTop: 0},700 );
		return false; 
	});
	
	
	$('.pg_stat_console_menu_elem').each(function() {
			$(this).click(function(){
				reset_up_down_buttons();		

				$( ".pg_stat_console_menu_elem" ).removeClass( "pg_stat_console_selected_elem" );
				$(this).addClass( "pg_stat_console_selected_elem" );
				all_xhr_abort();
									
			});
	});		
	
	$( "#logo" ).click(function(){
		$( "#sub_menu_start_dashboard" ).click();
	});
	

	$( "#sub_menu_start_dashboard" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();
		
		init_work_space();
		$( "#work_space" ).append( "<div style=\"width: 100%; margin: 0 auto;height:40px;text-align: center;\"></div><div id=\"graph_space\" style=\"\"></div>" );		
		$( "#work_space" ).append( sub_space );
		
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> Start Dashboard");
		
		$.ajax({ url: '/getDashboardConfig',
				type: 'post',
				data: JSON.stringify({ user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') }),
				success: function(data) {
					function build_dashboard(data_dashboard)
					{
						for (var i = 0; i < data_dashboard.length; i++) {	
							var dates = [];
							
							if( demo_dt_a !== "" && demo_dt_a !== 'undefined param name' &&
								demo_dt_b !== "" && demo_dt_b !== 'undefined param name' )
								dates = [demo_dt_a, demo_dt_b];
							else
								dates = make_dates_interval_str( data_dashboard[ i ][1] );
							
							if( data_dashboard[ i ][0] == "getLog" )
							{
								load_process.push( true );
								$( "#sub_space" ).empty();
								$.ajax({ url: '/getLog',
										type: 'post',
										data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), date_a: dates[0], date_b: dates[1], error: "true" } ),
										success: function(data) {
											$( "#sub_space" ).empty();
											$( "#sub_space" ).append( "<h2 class=\"scrollable_obj\" style =\"text-align: center;font-size: 16px;\">Last Errors</h2>" );
												if( data.length == 0 )
													$( "#sub_space" ).append( div_no_data );
												else
													$( "#sub_space" ).append( data );
												
												current_xhr.push( $.ajax({ url: '/getLog',
														type: 'post',
														data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), date_a: dates[0], date_b: dates[1], fatal: "true" } ),
														success: function(data) {
															load_process.pop();
															$( "#sub_space" ).append( "<h2 class=\"scrollable_obj\" style =\"text-align: center;font-size: 16px;\">Fatal Errors</h2>" );
																if( data.length == 0 )
																	$( "#sub_space" ).append( div_no_data );
																else
																	$( "#sub_space" ).append( data );
														},
														error: function(XMLHttpRequest, textStatus, errorThrown) {
																load_process.pop();
																if( textStatus !== "abort" ) 
																	show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
															}
												}) );											
										},
										error: function(XMLHttpRequest, textStatus, errorThrown) {
												if( textStatus !== "abort" ) 
													show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
										}
								});								
							}
							else
								graph_post( data_dashboard[ i ][0], dates[0], dates[1], function(){redraw_dashboard();} );
						}							
					}
					
					if( data.length == 0)
					{
						user_dashboard = [['getCPUStat',12],['getMemUsageStat',12],['getDiskUtilStat',12],['getNetworkTrafficStat',12]];
						build_dashboard( user_dashboard );
					} else
					{
						user_dashboard = data;
						build_dashboard( user_dashboard );	
					}					
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) show_error( textStatus, errorThrown, XMLHttpRequest.responseText );
					}
		});	
		
	});	

	$( "#button_show_status" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();
		init_work_space();
		get_current_status();
		$("#nav_str").text( "Check console status");
		load_process.push( true );
		current_xhr.push( $.ajax({ url: '/getConsoleStatusReport',
				type: 'post',
				data: JSON.stringify( {node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data')} ),
				success: function(data) {
					init_work_space();
					$( "#work_space" ).append( data );	
					reset_up_down_buttons();
					load_process.pop();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
					}
		}));	
		progress_notice( '<div style="font-size:25px;"><p>Checking pg_stat_console status...</p></div>' );
	});	
	
	$( "#button_show_db_status" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();
		init_work_space();
		get_current_db_status();
		$("#nav_str").text( current_node_name + " -> " + "Database maintenance status" );
		load_process.push( true );
		current_xhr.push( $.ajax({ url: '/getMaintenanceTasks',
				type: 'post',
				data: JSON.stringify( {node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data')} ),
				success: function(data) {
					init_work_space();
					$( "#work_space" ).append( data );
					reset_up_down_buttons();
					load_process.pop();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
					}
		}));	
		progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
	});	
	
	$( "#button_settings" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		init_work_space();	
		get_current_status();
		$("#nav_str").text( "Settings");
		load_process.push( true );
		current_xhr.push( $.ajax({ url: '/showUserConfig',
				type: 'post',
				data: JSON.stringify( {user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data')} ),
				success: function(data) {
					init_work_space();
					$( "#work_space" ).append( data );
					reset_up_down_buttons();
					load_process.pop();
					click_on_check_boxes_in_settings();				
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
					}
		}));	
		progress_notice( '<div style="font-size:25px;"><p>Loading configuration...</p></div>' );
	});	
	
	$( "#sub_menu_compare,#sub_menu_compare_2,#sub_menu_compare_2_2" ).click(function() {
		$(".pg_stat_console_goto_top").click();

		$("#nav_str").text( "Compare different metrics");
		
		set_date_time_filter_compare_params(4);
		$( "#work_space" ).append( "<div style=\"width: 100%; margin: 0 auto;height:40px;text-align: center;\"></div><div id=\"graph_space\" style=\"\"></div>" );		
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#cmp_param_1").val("getCPUStat");
		$("#cmp_param_2").val("getMemUsageStat");
		
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			var compare_dict = [];
			
			for (var i = 0; i < dashboard_dict.length; i++)	
				if( dashboard_dict[i][0] == $("#cmp_param_1").val() )
					compare_dict.push( dashboard_dict[i] );		

			for (var i = 0; i < dashboard_dict.length; i++)	
				if( dashboard_dict[i][0] == $("#cmp_param_2").val() )
					compare_dict.push( dashboard_dict[i] );	

			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			
			if($("#cmp_param_1").val() == $("#cmp_param_2").val() )
			{
				dlg_ok( "Error", "<p>Please enter different parameters</p>" );
			} else
			{
				if( check_dates_interval( $("#date_a").val(), $("#date_b").val(), 5 ) )
				{
					graph_post( $("#cmp_param_1").val(), $("#date_a").val(), $("#date_b").val(), function() { sort_charts_by_dict( dashboard_dict, compare_dict ); } );
					graph_post( $("#cmp_param_2").val(), $("#date_a").val(), $("#date_b").val(), function() { sort_charts_by_dict( dashboard_dict, compare_dict ); } );
				}
			}
		});	
		
	});
	
	$( "#sub_menu_compare_single,#sub_menu_compare_single_2,#sub_menu_compare_single_2_2" ).click(function() {
		$(".pg_stat_console_goto_top").click();

		$("#nav_str").text( "Compare single metric");
		
		set_date_time_filter_compare_single_params(4);
		$( "#work_space" ).append( "<div style=\"width: 100%; margin: 0 auto;height:40px;text-align: center;\"></div><div id=\"graph_space\" style=\"\"></div>" );		
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#cmp_param").val("getCPUStat");

		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			var compare_dict = [];
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			
			
			if(( $("#date_a").val() == $("#date2_a").val() ) && ( $("#date_b").val() == $("#date2_b").val() ) )
			{
				dlg_ok( "Error", "<p>Please enter different interval dates</p>" );
			} else
			{
				if( check_dates_interval( $("#date_a").val(), $("#date_b").val(), 5 ) && check_dates_interval( $("#date2_a").val(), $("#date2_b").val(), 5 ) )
					graph_post( $("#cmp_param").val(), $("#date_a").val(), $("#date_b").val(), 
						function() { 
						graph_post( $("#cmp_param").val(), $("#date2_a").val(), $("#date2_b").val() ); 
						});
			}
		});			
	});	
	
	$( "#sub_menu_disk_read" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Disk read");
		set_date_time_filter(4);
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
			
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getReadStat', $("#date_a").val(), $("#date_b").val() ) );
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	
	$( "#sub_menu_block_hit_db" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
			
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Block hit by databases");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getBlockHitDB', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	
	//------------------------------------------------------------------------------------
	$( "#sub_menu_cpu_usage" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();

		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> CPU");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			
			current_xhr.push( graph_post( 'getCPUStat', $("#date_a").val(), $("#date_b").val() ) );  
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	$( "#sub_menu_mem_usage" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> Memory usage");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getMemUsageStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	$( "#sub_menu_disk_util" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> Disk utilization");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getDiskUtilStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	$( "#sub_menu_disk_usage" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> Disk usage");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getDiskUsageStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	$( "#sub_menu_disk_wrqm_rrqm" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
			
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> Read/write requests merged per second");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getWRQMRRQMStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	$( "#sub_menu_disk_wr" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> Read/Write requests per second");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getWRStat', $("#date_a").val(), $("#date_b").val() ) );  
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	$( "#sub_menu_disk_rsec_wsec" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> Read/Write sectors from the device per second");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getRSecWSecStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	$( "#sub_menu_disk_avgrq" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> The average size of the requests");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getAVGRQStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	$( "#sub_menu_disk_avgqu" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> The average queue length of the requests");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getAVGQUStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	$( "#sub_menu_disk_await" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> The average time for I/O requestss");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getAWaitStat', $("#date_a").val(), $("#date_b").val() ) );
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	$( "#sub_menu_network_traffic" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> Network Traffic");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getNetworkTrafficStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	$( "#sub_menu_network_packets" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> Network Packets");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getNetworkPacketsStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});	
	$( "#sub_menu_network_errors" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		$("#nav_str").text( current_node_name + " -> " + "Hardware load -> Network Errors");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getNetworkErrorsStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	//------------------------------------------------------------------------------------
	
	$( "#sub_menu_bgwriter_stat" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Bgwriter stat");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getBgwriterStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
		
	$( "#sub_menu_block_read_db" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Block read by databases");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getBlockReadDB', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});	

	$( "#sub_menu_tup_write_db" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Tuples write by databases");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getTupWriteDB', $("#date_a").val(), $("#date_b").val() )); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});	
	
	$( "#sub_menu_tup_ret_fetch_db" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Tuples returned/fetched by databases");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getTupRetFetchDB', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});	
	
	
	$( "#sub_menu_autovac" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Autovacuum workers activity");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getAutovacStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});			
	
	$( "#sub_menu_conns" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Connections");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getConnsStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});		

	$( "#sub_menu_locks_db" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Locks");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getLocksStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});			
	
	$( "#sub_menu_tx_db" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Transactions by databases");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {

			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getTxDB', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});	

	$( "#sub_menu_deadlocks_db" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Deadlocks");
		set_date_time_filter(24);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getDeadlocksDB', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});	
	
	$( "#sub_menu_disk_write" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Disk write");
		set_date_time_filter(4);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			$( "#auto_refresh_div" ).fadeOut( "slow" );
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getWriteStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	
	
	$( "#sub_menu_seq_index_scans" ).click(function() {
		
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Disk Scans (seq/index)");
		set_date_time_filter(4);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getTupStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});	
		

	$( "#sub_menu_idx_quality" ).click(function() {
		
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Efficiency index scans");
		set_date_time_filter(4);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getIndexStat', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});	
	
	$( "#sub_menu_timing_queries" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Query durations");
		set_date_time_filter(12);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getQueryDurations', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	
	$('div[id^=sub_menu_][id$=_by_queries]').click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL queries -> " + $(this).text());
		set_date_time_filter(12);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'get' + selected_menu_elem.name.replace(/_/g , "").replace("submenu", "") , $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();
	});

	$( "#sub_menu_io_read" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> I/O Timings read by queries");
		set_date_time_filter(12);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getQueryIODurations', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});	

	$( "#sub_menu_blocks_by_queries_autoexp" ).click(function() {
		
		$(".pg_stat_console_goto_top").click();
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		$("#nav_str").text( current_node_name + " -> " + "PostgreSQL load -> Blocks by queries");
		set_date_time_filter(12);
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			$( "#graph_space" ).empty();
			current_xhr.push( graph_post( 'getQueryBlks', $("#date_a").val(), $("#date_b").val() ) ); 
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});		
	
	
	$( "#sub_menu_stat_activity" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();
		//hide_all_submenu();
		$("#nav_str").text( current_node_name + " -> " + "Typical queries -> Connections pg_stat_activity");
		load_process.push( true );
		$.ajax({ url: '/getActivity',
				type: 'post',
				data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(data) {
								init_work_space();
								$( "#work_space" ).append( data );
								apply_sort_tables();
								load_process.pop();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
					}
		});		
	});	
	
	$( "#sub_menu_locks" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();
		//hide_all_submenu();
		$("#nav_str").text( current_node_name + " -> " + "Typical queries -> Locks" );
		load_process.push( true );
		current_xhr.push( $.ajax({ url: '/getLocks',
				type: 'post',
				data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(data) {
								init_work_space();
								$( "#work_space" ).append( data );
								apply_sort_tables();
								load_process.pop();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
					}
		}));
		progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
	});	
	
	$( "#sub_menu_locks_by_pair" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();
		//hide_all_submenu();
		$("#nav_str").text( current_node_name + " -> " + "Typical queries -> Lock by pairs");
		load_process.push( true );
		current_xhr.push( $.ajax({ url: '/getLocksPairs',
				type: 'post',
				data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(data) {
								init_work_space();
								$( "#work_space" ).append( data );
									
								apply_sort_tables();
								apply_conn_man_buttons();
								load_process.pop();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
					}
		}));	
		progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );		
	});	

	$( "#sub_menu_stat_statements" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();
		//
		$("#nav_str").text( current_node_name + " -> " + "Typical queries -> Query statistic pg_stat_statements");
		load_process.push( true );
		$.ajax({ url: '/getStatements',
				type: 'post',
				data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(data) {
								init_work_space();
								$( "#work_space" ).append( data );
								apply_sort_tables();
								load_process.pop();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
					}
		});		
	});	

	$( "#sub_menu_long_queries" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();
		//
		$("#nav_str").text( current_node_name + " -> " + "Typical queries -> Long queries");
		load_process.push( true );
		$.ajax({ url: '/getLongQueries',
				type: 'post',
				data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(data) {
								init_work_space();
								$( "#work_space" ).append( data );
								apply_sort_tables();
								load_process.pop();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
					}
		});		
	});	

	$( "#sub_menu_table_sizes" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		//
		$("#nav_str").text( current_node_name + " -> " + "Typical queries -> Table sizes");
		load_process.push( true );
		current_xhr.push( $.ajax({ url: '/getTblSizes',
				type: 'post',
				data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(data) {
								init_work_space();
								$( "#work_space" ).append( data );
								load_process.pop();
								apply_sort_tables();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						load_process.pop();
						if( textStatus !== "abort" ) 
							show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
						else
						{
							$( "#sub_space" ).empty();
							$( "#sub_space" ).append( div_query_canceled );
						}
					}
		}) );
		progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
	});	

	$( "#sub_menu_unused_idxs" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();
		//
		$("#nav_str").text( current_node_name + " -> " + "Typical queries -> Unused indexes");
		load_process.push( true );
		current_xhr.push(  $.ajax({ url: '/getUnusedIdxs',
				type: 'post',
				data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(data) {
								init_work_space();
								$( "#work_space" ).append( data );
									
								load_process.pop();
								apply_sort_tables();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						load_process.pop();
						if( textStatus !== "abort" ) 
							show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
						else
						{
							$( "#sub_space" ).empty();
							$( "#sub_space" ).append( div_query_canceled );
						}
					}
		}));	
		progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
	});	

	$( "#sub_menu_idx_bloat" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		//
		$("#nav_str").text( current_node_name + " -> " + "Typical queries -> Index Bloat");
		load_process.push( true );
		current_xhr.push(  $.ajax({ url: '/getIndexBloat',
				type: 'post',
				data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(data) {
								init_work_space();
								$( "#work_space" ).append( data );
									
								load_process.pop();
								apply_sort_tables();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						load_process.pop();
						if( textStatus !== "abort" ) 
							show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
						else
						{
							$( "#sub_space" ).empty();
							$( "#sub_space" ).append( div_query_canceled );
						}
					}
		}));	
		progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
	});	
	
	$( "#sub_menu_tbl_bloat" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		//
		$("#nav_str").text( current_node_name + " -> " + "Typical queries -> Table Bloat");
		load_process.push( true );
		current_xhr.push(  $.ajax({ url: '/getTableBloat',
				type: 'post',
				data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(data) {
								init_work_space();
								$( "#work_space" ).append( data );
									
								load_process.pop();
								apply_sort_tables();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						load_process.pop();
						if( textStatus !== "abort" ) 
							show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
						else
						{
							$( "#sub_space" ).empty();
							$( "#sub_space" ).append( div_query_canceled );
						}
					}
		} ));	
		progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
	});		
	
	$( "#sub_menu_pg_config" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		//
		$("#nav_str").text( current_node_name + " -> " + "Typical queries -> PostgreSQL config");
		load_process.push( true );
		current_xhr.push( $.ajax({ url: '/getPGConfig',
				type: 'post',
				data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(data) {
								init_work_space();
								$( "#work_space" ).append( data );
									
								load_process.pop();
								apply_sort_tables();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						load_process.pop();
						if( textStatus !== "abort" ) 
							show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
						else
						{
							$( "#sub_space" ).empty();
							$( "#sub_space" ).append( div_query_canceled );
						}
					}
		}));	
		progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
	});				

	$( "#sub_menu_top_fetch" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		//
		$("#nav_str").text( current_node_name + " -> " + "Typical queries -> Top index/seq tup fetched");
		load_process.push( true );
		current_xhr.push( $.ajax({ url: '/getIdxSeqTupFetch',
				type: 'post',
				data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(data) {
								init_work_space();
								$( "#work_space" ).append( data );
									
								load_process.pop();
								apply_sort_tables();
				},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							load_process.pop();
							if( textStatus !== "abort" ) 
								show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
							else
							{
								$( "#sub_space" ).empty();
								$( "#sub_space" ).append( div_query_canceled );
							}
						}
		}));
		progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' );
	});		
	
	$( "#sub_menu_common_log" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		$("#nav_str").text( current_node_name + " -> " + "DB Logs -> Common DB log");
		init_work_space();		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		set_date_time_log_filter(3);
		$( "#work_space" ).append( sub_space );
		
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
		
		if( $('#time_len_g').length )         
		{	
			//duration
			//duration_g = t/f
			//duration_v = num
			
			var duration_g_state = true;
			if( $("#time_len_g").prop("checked") )
				duration_g_state = true;
			else
				duration_g_state = false;
				
			if( check_dates_interval( $("#date_a").val(), $("#date_b").val(), 3 ) == false )
				return;
			
			load_process.push( true );
			$( "#sub_space" ).empty();
			current_xhr.push( $.ajax({ url: '/getLog',
					type: 'post',
					data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), date_a: $("#date_a").val(), date_b: $("#date_b").val(), duration: "true", duration_g: duration_g_state, duration_v: $("#time_len_val").val() } ),
					success: function(data) {
						//set_date_time_filter();
						$( "#sub_space" ).empty();
						$( "#sub_space" ).append( data );
						load_process.pop();
						reset_up_down_buttons();
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							load_process.pop();
							if( textStatus !== "abort" ) 
								show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
							else
							{
								$( "#sub_space" ).empty();
								$( "#sub_space" ).append( div_query_canceled );
							}
						}
			}));
			progress_notice( '<div style="font-size:25px;"><p>DB logs loading...</p></div>' );
		} else {
		
			if( check_dates_interval( $("#date_a").val(), $("#date_b").val(), 3 ) == false )
				return;
			
			load_process.push( true );
			$( "#sub_space" ).empty();
			current_xhr.push( $.ajax({ url: '/getLog',
					type: 'post',
					data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), date_a: $("#date_a").val(), date_b: $("#date_b").val() } ),
					success: function(data) {
						//set_date_time_filter();
						$( "#sub_space" ).empty();
						$( "#sub_space" ).append( data );
						load_process.pop();
						reset_up_down_buttons();
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							load_process.pop();
							if( textStatus !== "abort" ) 
								show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
							else
							{
								$( "#sub_space" ).empty();
								$( "#sub_space" ).append( div_query_canceled );
							}
						}
			}));
			progress_notice( '<div style="font-size:25px;"><p>DB logs loading...</p></div>' );
		}
		});	
		$( "#apply_filter_button" ).click();		
	});

	$( "#sub_menu_log_errs" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		$("#nav_str").text( current_node_name + " -> " + "DB Logs -> Errors");
		init_work_space();		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		set_date_time_filter(4);
		$( "#work_space" ).append( sub_space );
		
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			
			if( check_dates_interval( $("#date_a").val(), $("#date_b").val(), 3 ) == false )
				return;
			load_process.push( true );
			$( "#sub_space" ).empty();
			current_xhr.push( $.ajax({ url: '/getLog',
					type: 'post',
					data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), date_a: $("#date_a").val(), date_b: $("#date_b").val(), error: "true" } ),
					success: function(data) {
						//set_date_time_filter();
						load_process.pop();
						$( "#sub_space" ).empty();
							if( data.length == 0 )
								$( "#sub_space" ).append( div_no_data );
							else
								$( "#sub_space" ).append( data );
						reset_up_down_buttons();
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							load_process.pop();
							if( textStatus !== "abort" ) 
								show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
							else
							{
								$( "#sub_space" ).empty();
								$( "#sub_space" ).append( div_query_canceled );
							}
						}
			}));
			progress_notice( '<div style="font-size:25px;"><p>DB logs loading...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});
	
	$( "#sub_menu_log_fatals" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		$("#nav_str").text( current_node_name + " -> " + "DB Logs -> Fatal errors");
		init_work_space();		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		set_date_time_filter(4);
		$( "#work_space" ).append( sub_space );
		
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			if( check_dates_interval( $("#date_a").val(), $("#date_b").val(), 3 ) == false )
				return;			
			load_process.push( true );
			$( "#sub_space" ).empty();
			current_xhr.push( $.ajax({ url: '/getLog',
					type: 'post',
					data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), date_a: $("#date_a").val(), date_b: $("#date_b").val(), fatal: "true" } ),
					success: function(data) {
						//set_date_time_filter();
						load_process.pop();
						$( "#sub_space" ).empty();
							if( data.length == 0 )
								$( "#sub_space" ).append( div_no_data );
							else
								$( "#sub_space" ).append( data );
						reset_up_down_buttons();
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							load_process.pop();
							if( textStatus !== "abort" ) 
								show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
							else
							{
								$( "#sub_space" ).empty();
								$( "#sub_space" ).append( div_query_canceled );
							}
						}
			}));
			progress_notice( '<div style="font-size:25px;"><p>DB logs loading...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});	
	
	$( "#sub_menu_log_locked" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		$("#nav_str").text( current_node_name + " -> " + "DB Logs -> Locked queries");
		init_work_space();		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		set_date_time_filter(4);
		$( "#work_space" ).append( sub_space );
		
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			if( check_dates_interval( $("#date_a").val(), $("#date_b").val(), 3 ) == false )
				return;			
			load_process.push( true );
			$( "#sub_space" ).empty();
			current_xhr.push( $.ajax({ url: '/getLog',
					type: 'post',
					data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), date_a: $("#date_a").val(), date_b: $("#date_b").val(), locked: "true" } ),
					success: function(data) {
						//set_date_time_filter();
						load_process.pop();
						if( data.length == 0 )
							$( "#sub_space" ).append( div_no_data );
						else
							$( "#sub_space" ).append( data );
						reset_up_down_buttons();
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							load_process.pop();
							if( textStatus !== "abort" ) 
								show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
							else
							{
								$( "#sub_space" ).empty();
								$( "#sub_space" ).append( div_query_canceled );
							}
						}
			}));
			progress_notice( '<div style="font-size:25px;"><p>DB logs loading...</p></div>' );
		});	
		$( "#apply_filter_button" ).click();		
	});		
	
	$( "#sub_menu_log_gt_minute" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		$("#nav_str").text( current_node_name + " -> " + "DB Logs -> Queries longer than a minute");
		init_work_space();		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		set_date_time_log_filter(3);
		$( "#work_space" ).append( sub_space );
		
		$("#time_len_g").attr('checked', 'checked');
		$("#time_len_val").val("60000");
		
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {

			//duration
			//duration_g = t/f
			//duration_v = num
			
			var duration_g_state = true;
			if( $("#time_len_g").prop("checked") )
				duration_g_state = true;
			else
				duration_g_state = false;
			
			if( check_dates_interval( $("#date_a").val(), $("#date_b").val(), 3 ) == false )
				return;			
			load_process.push( true );
			$( "#sub_space" ).empty();
			current_xhr.push( $.ajax({ url: '/getLog',
					type: 'post',
					data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), date_a: $("#date_a").val(), date_b: $("#date_b").val(), duration: "true", duration_g: duration_g_state, duration_v: $("#time_len_val").val() } ),
					success: function(data) {
						//set_date_time_filter();
						load_process.pop();
						if( data.length == 0 )
							$( "#sub_space" ).append( div_no_data );
						else
							$( "#sub_space" ).append( data );
						reset_up_down_buttons();	
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							load_process.pop();
							if( textStatus !== "abort" ) 
								show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
							else
							{
								$( "#sub_space" ).empty();
								$( "#sub_space" ).append( div_query_canceled );
							}
						}
			}));
			progress_notice( '<div style="font-size:25px;"><p>DB logs loading...</p></div>' );
		
		});	
		$( "#apply_filter_button" ).click();		
	});		
	
	$( "#sub_menu_log_lt_minute" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		$("#nav_str").text( current_node_name + " -> " + "DB Logs -> Queries shorter than a minute");
		init_work_space();		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		set_date_time_log_filter(3);
		$( "#work_space" ).append( sub_space );
		
		$("#time_len_l").attr('checked', 'checked');
		$("#time_len_val").val("60000");
		
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {

			//duration
			//duration_g = t/f
			//duration_v = num
			
			var duration_g_state = true;
			if( $("#time_len_g").prop("checked") )
				duration_g_state = true;
			else
				duration_g_state = false;
			
			if( check_dates_interval( $("#date_a").val(), $("#date_b").val(), 3 ) == false )
				return;			
			load_process.push( true );
			$( "#sub_space" ).empty();
			current_xhr.push( $.ajax({ url: '/getLog',
					type: 'post',
					data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), date_a: $("#date_a").val(), date_b: $("#date_b").val(), duration: "true", duration_g: duration_g_state, duration_v: $("#time_len_val").val() } ),
					success: function(data) {
						//set_date_time_filter();
						load_process.pop();
						if( data.length == 0 )
							$( "#sub_space" ).append( div_no_data );
						else
							$( "#sub_space" ).append( data );
						reset_up_down_buttons();	
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							load_process.pop();
							if( textStatus !== "abort" ) 
								show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
							else
							{
								$( "#sub_space" ).empty();
								$( "#sub_space" ).append( div_query_canceled );
							}
						}
			}));
			progress_notice( '<div style="font-size:25px;"><p>DB logs loading...</p></div>' );
		
		});	
		$( "#apply_filter_button" ).click();		
	});			
	
	$( "#sub_menu_log_downloader" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		$("#nav_str").text( current_node_name + " -> " + "DB Logs -> Log downloader");
		init_work_space();		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		set_date_time_filter(8);
		$( "#work_space" ).append( sub_space );
		
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {

		load_process.push( true );
		current_xhr.push( $.ajax({ url: '/getListLogFiles',
				type: 'post',
				data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), date_a: $("#date_a").val(), date_b: $("#date_b").val() } ),
				success: function(data) {
			
					$( "#sub_space" ).empty();
					$( "#sub_space" ).append( data );
					$($( "#sub_space" ).children()[0]).attr('style', 'margin-left: 0 px;');
						
					load_process.pop();
					apply_sort_tables();
				
					$(".log_download").unbind( "click" );
					$(".log_download").click(function(){
						load_process.push( true );
						current_xhr.push( $.ajax({ url: '/downloadLogFile',
								type: 'post',
								data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), file_name: $(this).attr("link_val") } ),
								success: function(data) {
									if( data === "No enougth rights" )
										dlg_ok( "Fail", " <p>No enougth rights</p>", function() { load_process.pop();} );
									else {
										load_process.pop();
										
										var link = document.createElement("a");
											var url = window.location.href.split( '/' );
											link.download = url[0] + "//" + url[2] + data;
											link.href = url[0] + "//" + url[2] + data;
											link.click();
										reset_up_down_buttons();
									}
								},
								error: function(XMLHttpRequest, textStatus, errorThrown) {
										load_process.pop();
										if( textStatus !== "abort" ) 
											show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
										else
										{
											$( "#sub_space" ).empty();
											$( "#sub_space" ).append( div_query_canceled );
										}
									}
						}));
						progress_notice( '<div style="font-size:25px;"><p>Packing log file...</p></div>' );									
					});		
				
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						load_process.pop();
						if( textStatus !== "abort" ) 
							show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
						else
						{
							$( "#sub_space" ).empty();
							$( "#sub_space" ).append( div_query_canceled );
						}
					}
		}));	
		progress_notice( '<div style="font-size:25px;"><p>Get DB logs list files...</p></div>' );
	
		});	
		$( "#apply_filter_button" ).click();
	});	
	
	
	function history_click()
	{	
		$(".date_link").click(function () {
			load_process.push( true );
			current_xhr.push( $.ajax({
				type: "POST",
				url: '/getActivityHistory',
				data: JSON.stringify( { date_a: $("#date_a").val(), date_b: $("#date_b").val(), date_s: $(this).text(), node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(response) {
					$( "#sub_space" ).empty();
					$( "#sub_space" ).append( response );
					
					$(".date_link").unbind( "click" );
					load_process.pop();				
					apply_sort_tables();
					history_click();	
				},
				error: function(err) {
					if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
				}
			}));
			progress_notice( '<div style="font-size:25px;"><p>Connections history loading...</p></div>' );
		});								
	}	
	
	$( "#sub_menu_conn_snapshots" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		$("#nav_str").text( current_node_name + " -> " + "Connection management -> Snapshots of connections and locks");
		init_work_space();		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		set_date_time_filter(2);
		$( "#work_space" ).append( sub_space );
		apply_sort_tables();
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			if( check_dates_interval( $("#date_a").val(), $("#date_b").val(), 3 ) == false )
				return;
			load_process.push( true );
			$.ajax({ url: '/getActivityHistory',
					type: 'post',
					data: JSON.stringify( { date_a: $("#date_a").val(), date_b: $("#date_b").val(), node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
					success: function(data) {
						//set_date_time_filter();
						$( "#sub_space" ).empty();
						$( "#sub_space" ).append( data );
						//$( ".report_table" ).css( "margin-left", "0px" );
						//$( ".report_table" ).css( "word-break", "normal" );
						
						$(".date_link").unbind( "click" );
						 load_process.pop();
						history_click();
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
						}
			});
		});	
		$( "#apply_filter_button" ).click();		
	});	


	function history_ext_click()
	{	
		$(".load_snapshot").unbind( "click" );
		$(".load_snapshot").click(function () {

			$('.bordered tr').each(function (i, row) {
				$(row).css("font-weight", "normal");
				$(this).closest('tr').css('color','#2e3846');
			});
			$(this).closest('tr').css('font-weight','bold');
			$(this).closest('tr').css('color','#795aac');

			load_process.push( true );
			current_xhr.push( $.ajax({
				type: "POST",
				url: '/getHistoryBySnId',
				data: JSON.stringify( { sn_id: $(this).attr("link_val"), node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
				success: function(response) {
					$( "#sub_space_2" ).empty();
					$( "#sub_space_2" ).append( response );
					load_process.pop();				
					apply_sort_tables();
					$( ".pg_stat_console_step_down" ).click();				
				},
				error: function(err) {
					if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
				}
			}));
			progress_notice( '<div style="font-size:25px;"><p>Snaphot loading...</p></div>' );
		});								
	}	
	
	$( "#sub_menu_conn_snapshots_ext" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		$("#nav_str").text( current_node_name + " -> " + "Connection management -> Snapshots of connections and locks [extended]");
		init_work_space();		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = false;
		hide_autorefresh();
		
		set_date_time_filter(2);
		$( "#work_space" ).append( sub_space );
		$( "#work_space" ).append( sub_space_2 );
		apply_sort_tables();
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			if( check_dates_interval( $("#date_a").val(), $("#date_b").val(), 3 ) == false )
				return;			
			load_process.push( true );
			current_xhr.push( $.ajax({ url: '/getActivityHistoryExt',
					type: 'post',
					data: JSON.stringify( { date_a: $("#date_a").val(), date_b: $("#date_b").val(), node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data') } ),
					success: function(data) {

						$( "#sub_space" ).empty();
						$( "#sub_space" ).append( data );
						$( "#sub_space_2" ).empty();
						load_process.pop();				
						apply_sort_tables();	
						history_ext_click();
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
						}
			}));
			progress_notice( '<div style="font-size:25px;"><p>Connections history loading...</p></div>' , current_xhr )
		});	
		$( "#apply_filter_button" ).click();		
	});		
	
	
	$( "#sub_menu_conn_old" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		$("#nav_str").text( current_node_name + " -> " + "Connection management -> Old unused connections");
		init_work_space();		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();
		
		set_old_conn_filter();
		$( "#work_space" ).append( sub_space );
		apply_sort_tables();
		$( "#apply_filter_button").unbind( "click" );
		$( "#apply_filter_button" ).click(function() {
			load_process.push( true );
			current_xhr.push( $.ajax({ url: '/getOldConns',
					type: 'post',
					data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), conn_age: $("#conn_age").val() } ),
					success: function(data) {
						$( "#sub_space" ).empty();
						$( "#sub_space" ).append( data );
						load_process.pop();				
						apply_sort_tables();
						apply_conn_man_buttons();
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
						}
			}));
			progress_notice( '<div style="font-size:25px;"><p>Query executing...</p></div>' , current_xhr )
		});	
		$( "#apply_filter_button" ).click();		
	});			
	
	function apply_conn_man_buttons()
	{
		$(".stop_query").unbind( "click" );
		$(".stop_query").click(function(){
			var pid_val = $(this).attr("link_val");
			load_process.push( true );
			current_xhr.push( $.ajax({ url: '/stopQuery',
					type: 'post',
					data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), pid: pid_val, command: "cancel" } ),
					success: function(data) {
						if( data === 'true' || data === 'True' )
						{
							dlg_ok( "Sucess", " <p>Query " + pid_val + " cancelled</p>");
						}
						if( data === 'false' || data === 'False' || data === 'No enougth rights' )
						{
							dlg_ok( "Fail", " <p>Query " + pid_val + " can't cancel. No enougth rights.</p>");
						}
						load_process.pop();
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							load_process.pop();
							if( textStatus !== "abort" ) 
								show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
							else
							{
								$( "#sub_space" ).empty();
								$( "#sub_space" ).append( div_query_canceled );
							}
						}
			}));								
		});		
		$(".kill_connect").unbind( "click" );
		$(".kill_connect").click(function(){
			var pid_val = $(this).attr("link_val");
			load_process.push( true );
			current_xhr.push( $.ajax({ url: '/stopQuery',
					type: 'post',
					data: JSON.stringify( { node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data'), pid: pid_val, command: "kill" } ),
					success: function(data) {
						if( data === 'true' || data === 'True' )
						{
							dlg_ok( "Sucess", " <p>Connection " + pid_val + " killed</p>");
						}
						if( data === 'false' || data === 'False' || data === 'No enougth rights' )
						{
							dlg_ok( "Fail", " <p>Connection " + pid_val + " can't kill</p>");
						}
						load_process.pop();
					},
					error: function(XMLHttpRequest, textStatus, errorThrown) {
							load_process.pop();
							if( textStatus !== "abort" ) 
								show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); 
							else
							{
								$( "#sub_space" ).empty();
								$( "#sub_space" ).append( div_query_canceled );
							}
						}
			}));									
		});		
	}
	
	$( "#sub_menu_conn_management" ).click(function() {
		$(".pg_stat_console_goto_top").click();
		
		$("#nav_str").text( current_node_name + " -> " + "Connection management -> Connection management");
		init_work_space();	
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();

		$( "#work_space" ).append( sub_space );
		apply_sort_tables();
		load_process.push( true );
		$.ajax({ url: '/getConnManagement',
				type: 'post',
				data: JSON.stringify( {node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data')} ),
				success: function(data) {
					init_work_space();
					$( "#work_space" ).append( data );
						
					load_process.pop();
					apply_sort_tables();
					apply_conn_man_buttons();
					
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
					}
		});
	
	});	

	$( "#sub_menu_processes" ).click(function() {
		$(".pg_stat_console_goto_top").click();

		$("#nav_str").text( current_node_name + " -> " + "Connection management -> Server processes (ps)");
		init_work_space();	
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();

		$( "#work_space" ).append( sub_space );
		apply_sort_tables();
		load_process.push( true );
		current_xhr.push( $.ajax({ url: '/getServerProcesses',
				type: 'post',
				data: JSON.stringify( {node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data')} ),
				success: function(data) {
					init_work_space();
					$( "#work_space" ).append( data );
						
					load_process.pop();
					apply_sort_tables();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
					}
		}));
		progress_notice( '<div style="font-size:25px;"><p>Server processes list loading...</p></div>' );
	});	
	
	$( "#sub_menu_io_processes" ).click(function() {
		$(".pg_stat_console_goto_top").click();

		$("#nav_str").text( current_node_name + " -> " + "Connection management -> Server processes (iotop)");
		init_work_space();	
		
		selected_menu_elem.name = this.id;
		selected_menu_elem.auto_refresh = true;
		show_autorefresh();

		$( "#work_space" ).append( sub_space );
		apply_sort_tables();
		load_process.push( true );
		current_xhr.push( $.ajax({ url: '/getIOServerProcesses',
				type: 'post',
				data: JSON.stringify( {node_name: current_node_name, user_config: localStorage.getItem('user_config'), user_auth_data: localStorage.getItem('user_auth_data')} ),
				success: function(data) {
					init_work_space();
					$( "#work_space" ).append( data );
						
					load_process.pop();
					apply_sort_tables();
				},
				error: function(XMLHttpRequest, textStatus, errorThrown) {
						if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
					}
		}));
		progress_notice( '<div style="font-size:25px;"><p>Server processes list loading...</p></div>' );
	});
	
	$( "#button_exit" ).click(function() {
		$(".pg_stat_console_step_down").fadeOut(200, function(){});
		$(".pg_stat_console_step_up").fadeOut(200, function(){});
		$(".pg_stat_console_goto_top").fadeOut(200, function(){});

		localStorage.removeItem('user_config');
		localStorage.removeItem('user_auth_data');
		
		hide_common_div();
		call_login_dialog();
	});

	$( "#button_refresh" ).click(function() {
			$( "#" + selected_menu_elem.name ).click();
	});

	$('#panel_close').click(function(){
		if( details_closed ){
			$('#details').css("visibility", "visible");
			details_closed = false;		
		} else {
			$('#details').css("visibility", "hidden");
			details_closed = true;
			$('.canvasjs-chart-tooltip').css("visibility", "visible");
		}
	});	
	$('#nodes_select').on('change', function() {
		current_node_name = this.value;
		set_user_auth_data( "selected_node_name", current_node_name );
		$( "#" + selected_menu_elem.name ).click();
		$('#db_status_panel').css('visibility', 'hidden');
		$("#db_status_panel" ).fadeOut( "slow" );
		get_current_status();
		get_uptime();
		get_current_node_info();
	});
	$('.pg_stat_console_left').click(function(){
		left_menu.open();
	});	
}

function set_all_mouseenter_events()
{
	$( "#menu" ).mouseenter(function( event ) {
		hide_all_submenu();
	});		

	$( "#main_info" ).mouseenter(function( event ) {
		hide_all_submenu();		
	});	
	
	$( "#work_space" ).mouseenter(function( event ) {
		hide_all_submenu();		
	});	
	
	$( "#user_panel" ).mouseenter(function( event ) {
		hide_all_submenu();		
	});		

	$( "#navigation_panel" ).mouseenter(function( event ) {
		hide_all_submenu();		
	});	
	
	$( "#menu_serv_load" ).mouseenter(function( event ) {
		$('#sub_menu_1').fadeIn( 150 );
		$('#sub_menu_2').fadeOut( 150 );
		$('#sub_menu_2_2').fadeOut( 150 );
		$('#sub_menu_3').fadeOut( 150 );
		$('#sub_menu_4').fadeOut( 150 );
		$('#sub_menu_5').fadeOut( 150 );
	});	
	$( "#menu_pg_load" ).mouseenter(function( event ) {
		$('#sub_menu_1').fadeOut( 150 );
		$('#sub_menu_2').fadeIn( 150 );
		$('#sub_menu_2_2').fadeOut( 150 );
		$('#sub_menu_3').fadeOut( 150 );
		$('#sub_menu_4').fadeOut( 150 );
		$('#sub_menu_5').fadeOut( 150 );
	});	
	$( "#menu_pg_queries" ).mouseenter(function( event ) {
		$('#sub_menu_1').fadeOut( 150 );
		$('#sub_menu_2').fadeOut( 150 );
		$('#sub_menu_2_2').fadeIn( 150 );
		$('#sub_menu_3').fadeOut( 150 );
		$('#sub_menu_4').fadeOut( 150 );
		$('#sub_menu_5').fadeOut( 150 );
	});		
	$( "#menu_typically_queries" ).mouseenter(function( event ) {
		$('#sub_menu_1').fadeOut( 150 );
		$('#sub_menu_2').fadeOut( 150 );
		$('#sub_menu_2_2').fadeOut( 150 );
		$('#sub_menu_3').fadeIn( 150 );
		$('#sub_menu_4').fadeOut( 150 );
		$('#sub_menu_5').fadeOut( 150 );
	});	
	$( "#menu_logs" ).mouseenter(function( event ) {
		$('#sub_menu_1').fadeOut( 150 );
		$('#sub_menu_2').fadeOut( 150 );
		$('#sub_menu_2_2').fadeOut( 150 );
		$('#sub_menu_3').fadeOut( 150 );
		$('#sub_menu_4').fadeIn( 150 );
		$('#sub_menu_5').fadeOut( 150 );
	});	
	$( "#menu_conn_manage" ).mouseenter(function( event ) {
		$('#sub_menu_1').fadeOut( 150 );
		$('#sub_menu_2').fadeOut( 150 );
		$('#sub_menu_2_2').fadeOut( 150 );
		$('#sub_menu_3').fadeOut( 150 );
		$('#sub_menu_4').fadeOut( 150 );
		$('#sub_menu_5').fadeIn( 150 );
	});				
}

function set_load_process()
{
	if( load_process.length == 0 && load_process_closed == false )
	{
		close_flavr_container();
		load_process_closed = true;
	}
	
	if( load_process.length == 0 )
		hide_progress();
	else
		show_progress();	
}

function set_auto_refresh()
{
	if( auto_refresh_counter == 0 )
		auto_refresh_counter = refresh_interval;
		
	if( auto_refresh_counter == 1 )
	{
		if( selected_menu_elem.auto_refresh && $("#auto_refresh").is(':checked') ) 
		{
			$( "#" + selected_menu_elem.name ).click();
		}
	}

	if( $("#auto_refresh").is(':checked') ) 
		$("#auto_refresh_div").html("<input id=\"auto_refresh\" type=\"checkbox\" name=\"auto_refresh\" value=\"a1\" checked>Auto refresh (" + (auto_refresh_counter - 1 ).toString() + ")");
	else
		$("#auto_refresh_div").html("<input id=\"auto_refresh\" type=\"checkbox\" name=\"auto_refresh\" value=\"a1\">Auto refresh");		

	
	auto_refresh_counter -= 1;	
}

function set_all_scroll_events()
{
	var e = $(".pg_stat_console_goto_top");
	
	function show_scrollTop(){
		( $('#main_work_space').scrollTop()>300 ) ? 
		e.fadeIn(300, function(){}) : 
		e.fadeOut(300);
	}
	$('#main_work_space').scroll( function(){show_scrollTop()} ); show_scrollTop();	

	$('#main_work_space').scroll(function() {                  
		var currentScroll = $('#main_work_space').scrollTop(); 
		$('.fix_div').css({                     
			"margin-top": -300 + currentScroll

		});
	});		
}

function get_custom_param( pname, func )
{
	$.ajax({ url: '/getCustomParam',
			type: 'post',
			data: JSON.stringify( { param_name: pname } ),
			success: function(data) {
				if( typeof func !== 'undefined' )
					func( data["result"] );
			},
			error: function(XMLHttpRequest, textStatus, errorThrown) {
					if( textStatus !== "abort" ) { show_error( textStatus, errorThrown, XMLHttpRequest.responseText ); load_process.pop(); }
				}
	});
}

function get_custom_params()
{
	get_custom_param( 'application_title', function(v) { 
				title_val = v;
				$("#app_name").text( title_val );
				document.title = title_val;
	});
	get_custom_param( 'demo_dt_a', function(v) { 
				demo_dt_a = v;
	});
	get_custom_param( 'demo_dt_b', function(v) { 
				demo_dt_b = v;
	});
}

function create_3d_menu()
{
	left_menu = Meny.create({
		menuElement: document.querySelector( '#menu' ),
		contentsElement: document.querySelector( '#main_work_space' ),
		position: 'left',
		width: 260,
		width_ext: 260*3,
		threshold: 10,
		angle: 20,
		transitionDuration: '0.4s',
		transitionEasing: 'ease',
		gradient: 'rgba(0,0,0,0.10) 0%, rgba(0,0,0,0.35) 100%)',
		touch: true
	});
	
	left_menu.addEventListener( 'open', function() {
		$("#nav_str").css({"margin-left":"20px"}).animate({"margin-left":"280px"}, "fast");

	} );
	
	left_menu.addEventListener( 'close', function() {
		$("#nav_str").css({"margin-left":"280px"}).animate({"margin-left":"20px"}, "slow");
		hide_all_submenu();
	} );		
}

function pg_stat_console_init()
{
	create_3d_menu();
	
	//all events
	set_all_click_events();
	set_all_scroll_events();
	set_all_mouseenter_events();
	get_custom_params();
	get_uptime();
	check_user_name_hash();
	get_refresh_interval();
	get_current_user_type();
	get_current_status();
	get_current_db_status();	
	set_nodes();
	
	//configure all timers
	setInterval( function() {
		get_uptime()
	}, 60000*3);
	
	setInterval( function() {
		get_current_status();
		get_current_node_info();
	}, 60000*3);

	setInterval( function() {
		get_current_db_status()
	}, 20000);	
	
	setInterval( function() {
		set_load_process()
	}, 200);

	setInterval( function() {
		set_auto_refresh();
	}, 1000 );	
}