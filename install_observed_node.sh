#!/bin/bash

show_help()
{
	echo
	echo "---------------------------------------------------"
	echo "Parameters"
	echo "---------------------------------------------------"
	echo "--main-db-host 	- main database host"
	echo "--main-db-port 	- main database port"
	echo "--main-db-name 	- name of main database"
	echo "--main-db-user 	- main database user"
	echo "--main-db-passw	- main database user password"
	echo "--no-main-db	- if only pg_stat_monitor will be used"
	echo
	echo "--db-host 	- database host"
	echo "--db-port 	- database port"
	echo "--db-names 	- names of databases to collect statistics (for example: --db-names=db_a,db_b or --db-names=ALL)"
	echo "--db-user 	- database user"
	echo "--db-passw 	- database user password"
	echo "--no-db	 	- if only pg_stat_monitor and (or) pg_stat_log_scanner will be used"
	echo
	echo "--psc-node-name 			- name of current node"
	echo "--psc-node-descr 			- description of current node"
	echo "--psc-node-host 			- host of current node"
	echo "--psc-time-zone 			- current timezone"
	echo "--no-pg-stat-monitor 			- disable pg_stat_monitor"
	echo "--pg-stat-monitor-port 			- pg_stat_monitor port"
	echo "--pg-stat-monitor-allow-hosts 		- allowed hosts for pg_stat_monitor"
	echo "--no-pg-stat-log-scanner 		- disable pg_stat_log_scanner"	
	echo "--psc-pg-log-dir 		- pg_log directory for pg_stat_log_scanner and pg_stat_monitor"
	echo
	echo "--pg-configure/pg-no-configure						- path to postgresql.conf for configuring"	
	echo "--psc-install/psc-no-install 						- install pg_stat_console services (all) or not"
	echo "--psc-run/psc-no-run 						- run pg_stat_console services or not"
	echo "--pg-stat-monitor-run/pg-stat-monitor-no-run 				- run pg_stat_monitor service or not"
	echo "--pg-stat-sys-run/pg-stat-sys-no-run 					- run pg_stat_sys service or not"
	echo "--pg-stat-log-scanner-run/pg-stat-log-scanner-no-run			- run pg_stat_log_scanner service or not"	

	echo '
---------------------------------------------------
Usage
---------------------------------------------------
chmod +x install_observed_node.sh

./install_observed_node.sh

	OR

./install_observed_node.sh --no-main-db --db-host=127.0.0.1 --db-port=6432 --db-names=ALL --db-user=app_user --psc-time-zone="Europe/Moscow"

	OR

./install_observed_node.sh \
--main-db-host=127.0.0.1 --main-db-port=6432 --main-db-name=sys_stat --main-db-user=app_user --main-db-passw=app_user \
--db-host=127.0.0.1 --db-port=6432 --db-names=ALL --db-user=app_user --db-passw=app_user \
--pg-configure \
--psc-time-zone="Europe/Moscow" --pg-stat-monitor-port=8889 --pg-stat-monitor-allow-hosts="127.0.0.1" \
--psc-node-name="my test node" --psc-node-descr="test node descr" --psc-node-host="127.0.0.1" --psc-install \
--psc-pg-log-dir="/var/log/pg_log" --psc-run --pg-stat-monitor-run --pg-stat-sys-run --pg-stat-log-scanner-run

	OR
	
./install_observed_node.sh \
--psc-install --pg-stat-sys-run --pg-stat-log-scanner-run --pg-stat-log-scanner-run
'
}

no_db=0

while [ "$1" != "" ]; do
	PARAM=`echo $1 | awk -F= '{print $1}'`
	VALUE=`echo $1 | awk -F= '{print $2}'`
	case $PARAM in
		-h | --help)
			show_help
			exit
			;;
		--main-db-host)
			main_db_host=$VALUE
			;;
		--main-db-port)
			main_db_port=$VALUE
			;;
		--main-db-name)
			main_db_name=$VALUE
			;;
		--main-db-user)
			main_db_user=$VALUE
			;;
		--main-db-passw)
			main_db_passw=$VALUE
			;;
		--no-main-db)
			no_main_db=1
			;;
		--db-host)
			db_host=$VALUE
			;;
		--db-port)
			db_port=$VALUE
			;;
		--db-names)
			db_names=$VALUE
			;;
		--db-user)
			db_user=$VALUE
			;;
		--db-passw)
			db_passw=$VALUE
			;;
		--no-db)
			no_db=1
			;;
		--psc-time-zone)
			psc_time_zone=$VALUE
			;;
		--no-pg-stat-sys)
			no_pg_stat_sys=1
			;;
		--no-pg-stat-monitor)
			no_pg_stat_monitor=1
			;;
		--pg-stat-monitor-port)
			pg_stat_monitor_port=$VALUE
			;;
		--pg-stat-monitor-allow-hosts)
			pg_stat_monitor_allow_hosts=$VALUE
			;;
		--psc-node-name)
			psc_node_name=$VALUE
			;;
		--psc-node-descr)
			psc_node_descr=$VALUE
			;;
		--psc-node-host)
			psc_node_host=$VALUE
			;;
		--no-pg-stat-log-scanner)
			no_pg_stat_log_scanner=1
			;;
		--psc-pg-log-dir)
			psc_pg_log_dir=$VALUE
			;;
		--pg-configure)
			pg_configure=$VALUE
			;;
		--pg-no-configure)
			pg_configure=0
			;;	
		--psc-install)
			psc_install=1
			;;
		--psc-no-install)
			psc_install=0
			;;
		--psc-run)
			psc_run=1
			;;
		--psc-no-run)
			psc_run=0
			;;
		--pg-stat-monitor-run)
			pg_stat_monitor_run=1
			;;
		--pg-stat-monitor-no-run)
			pg_stat_monitor_run=0
			;;
		--pg-stat-sys-run)
			pg_stat_sys_run=1
			;;
		--pg-stat-sys-no-run)
			pg_stat_sys_run=0
			;;
		--pg-stat-log-scanner-run)
			pg_stat_log_scanner_run=1
			;;
		--pg-stat-log-scanner-no-run)
			pg_stat_log_scanner_run=0
			;;
		*)
			echo "ERROR: unknown parameter \"$PARAM\""
			show_help
			exit 1
			;;
	esac
	shift
done

if [[ !(-z $(ps -ef | grep pg_stat_monitor.py | grep -v grep | awk '{print $2}')) ]] && \
	[[ !(-z $(ps -ef | grep pg_stat_log_scanner.py | grep -v grep | awk '{print $2}')) ]] && \
	[[ !(-z $(ps -ef | grep pg_stat_sys.py | grep -v grep | awk '{print $2}')) ]]; then
	echo "pg_stat_monitor, pg_stat_log_scanner and pg_stat_sys already runned"
	exit
fi

if [ -z "$no_main_db" ]; then
	if [ -z "$main_db_host" ]; then
		echo
		echo -n "Enter main DB host and press [ENTER] (default 127.0.0.1):"
		read main_db_host

		if [ -z "$main_db_host" ]; then
			main_db_host="127.0.0.1"
			echo "DB host is empty, using $main_db_host"
		fi
	fi

	if [ -z "$main_db_port" ]; then
		echo
		echo -n "Enter main DB port and press [ENTER] (default 6432):"
		read main_db_port

		if [ -z "$main_db_port" ]; then
			main_db_port="6432"
			echo "DB port is empty, using $main_db_port"
		fi
	fi

	if [ -z "$main_db_name" ]; then
		echo
		echo -n "Enter main DB name and press [ENTER] (default sys_stat):"
		read main_db_name

		if [ -z "$main_db_name" ]; then
			main_db_name="sys_stat"
			echo "DB name is empty, using '$main_db_name'"
		fi
	fi

	if [ -z "$main_db_user" ]; then
		echo
		echo -n "Enter main DB user and press [ENTER] (default app_user):"
		read main_db_user

		if [ -z "$main_db_user" ]; then
			main_db_user="app_user"
			echo "DB user is empty, using '$main_db_user'"
		fi
	fi

	if [ -z "$main_db_passw" ]; then
		echo
		echo -n "Enter main DB user password and press [ENTER] (default app_user):"
		stty -echo
		read main_db_passw; echo
		stty echo

		if [ -z "$main_db_passw" ]; then
			main_db_passw="app_user"
			echo "DB user password is empty, using '$main_db_passw'"
		fi
	fi
fi

if [ "$no_db" == 0 ]; then
	if [ -z "$db_host" ]; then
		echo
		echo -n "Enter DB host and press [ENTER] (default 127.0.0.1):"
		read db_host

		if [ -z "$db_host" ]; then
			db_host="127.0.0.1"
			echo "DB host is empty, using $db_host"
		fi
	fi

	if [ -z "$db_port" ]; then
		echo
		echo -n "Enter DB port and press [ENTER] (default 6432):"
		read db_port

		if [ -z "$db_port" ]; then
			db_port="6432"
			echo "DB port is empty, using $db_port"
		fi
	fi

	if [ -z "$db_names" ]; then
		echo
		echo -n "Enter DB names and press [ENTER] (default ALL):"
		read db_names

		if [ -z "$db_names" ]; then
			db_names="ALL"
			echo "DB name is empty, using '$db_names'"
		fi
	fi

	if [ -z "$db_user" ]; then
		echo
		echo -n "Enter DB user and press [ENTER] (default app_user):"
		read db_user

		if [ -z "$db_user" ]; then
			db_user="app_user"
			echo "DB user is empty, using '$db_user'"
		fi
	fi

	if [ -z "$db_passw" ]; then
		echo
		echo -n "Enter DB user password and press [ENTER] (default app_user):"
		stty -echo
		read db_passw; echo
		stty echo

		if [ -z "$db_passw" ]; then
			db_passw="app_user"
			echo "DB user password is empty, using '$db_passw'"
		fi
	fi
fi

if [ -z "$psc_time_zone" ]; then
	echo
	echo -n "Enter timezone and press [ENTER] (default Europe/Moscow):"
	read psc_time_zone
	
	if [ -z "$psc_time_zone" ]; then
		psc_time_zone="Europe/Moscow"
		echo "Timezone is empty, using '$psc_time_zone'"
	fi
fi

if [ -z "$no_pg_stat_monitor" ] && [ -z "$pg_stat_monitor_port" ]; then
	echo
	echo -n "Enter pg_stat_monitor port and press [ENTER] (default 8889):"
	read pg_stat_monitor_port
	
	if [ -z "$pg_stat_monitor_port" ]; then
		pg_stat_monitor_port="8889"
		echo "pg_stat_monitor port is empty, using '$pg_stat_monitor_port'"
	fi
fi

if [ -z "$no_pg_stat_monitor" ] && [ -z "$pg_stat_monitor_allow_hosts" ]; then
	echo
	echo -n "Enter allowed hosts for pg_stat_monitor [ENTER] (default 127.0.0.1):"
	read pg_stat_monitor_allow_hosts
	
	if [ -z "$pg_stat_monitor_allow_hosts" ]; then
		pg_stat_monitor_allow_hosts="127.0.0.1"
		echo "Allowed hosts for pg_stat_monitor is empty, using '$pg_stat_monitor_allow_hosts'"
	fi
fi

if [ -z "$psc_node_name" ]; then
	echo
	echo -n "Enter node name and press [ENTER] (default 'observed node'):"
	read psc_node_name
	
	if [ -z "$psc_node_name" ]; then
		psc_node_name="observed node"
		echo "Node name is empty, using '$psc_node_name'"
	fi
fi

if [ -z "$psc_node_descr" ]; then
	echo
	echo -n "Enter node description and press [ENTER] (default 'observed node'):"
	read psc_node_descr
	
	if [ -z "$psc_node_descr" ]; then
		psc_node_descr="observed node"
		echo "Node description is empty, using '$psc_node_descr'"
	fi
fi

if [ -z "$psc_node_host" ]; then
	echo
	echo -n "Enter node host and press [ENTER] (default $HOSTNAME):"
	read psc_node_host
	
	if [ -z "$psc_node_host" ]; then
		psc_node_host=$HOSTNAME
		echo "Node host is empty, using '$psc_node_host'"
	fi
fi

if [ "$no_db" == 0 ] && [ -z "$psc_pg_log_dir" ]; then
	echo
	echo -n "Enter pg_log directory location and press [ENTER] (default '/var/log/pg_log'):"
	read psc_pg_log_dir
	
	if [ -z "$psc_pg_log_dir" ]; then
		psc_pg_log_dir="/var/log/pg_log"
		echo "pg_log directory location is empty, using '$psc_pg_log_dir'"
	fi
fi

if [ "$db_names" == "ALL" ]; then
	if [ -z "$main_db_name" ]; then
		dbs_cond="datname <> 'postgres'"
	else
		dbs_cond="datname <> 'postgres' and datname <> '${main_db_name}'"	
	fi
	
	if [ "$db_port" == '6432' ]; then
		db_port_direct='5432'
	fi
	
	results=($(su -l postgres -c "PGPASSWORD='${db_passw}'; psql -A -t -p '${db_port_direct}' -h '${db_host}' -U '${db_user}' -d 'postgres' -c \"select datname from pg_database where datistemplate = false and ${dbs_cond}\""))
	cnt_recs=${#results[@]}
	for (( i=0 ; i<cnt_recs ; i++ ))
	do
		DB_NAME_I=`echo ${results[$i]} | awk -F'|' '{print $1}'`
		psc_databases_pypg+="$DB_NAME_I = postgresql+pypostgresql://$db_user:$db_passw@$db_host:$db_port/$DB_NAME_I\n"
		psc_databases_pq+="$DB_NAME_I = pq://$db_user:$db_passw@$db_host:$db_port/$DB_NAME_I\n"
	done
else
	for DB_NAME_I in $(echo $db_names | tr "," "\n")
	do
		psc_databases_pypg+="$DB_NAME_I = postgresql+pypostgresql://$db_user:$db_passw@$db_host:$db_port/$DB_NAME_I\n"
		psc_databases_pq+="$DB_NAME_I = pq://$db_user:$db_passw@$db_host:$db_port/$DB_NAME_I\n"
	done
fi

PSC_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
NEW_CONF_STAT_SYS=$PSC_PATH/conf/pg_stat_sys.conf
cp $PSC_PATH/conf/pg_stat_sys.conf.example $NEW_CONF_STAT_SYS
NEW_CONF_MONITOR=$PSC_PATH/conf/pg_stat_monitor.conf
cp $PSC_PATH/conf/pg_stat_monitor.conf.example $NEW_CONF_MONITOR
NEW_CONF_LOG_SCANNER=$PSC_PATH/conf/pg_stat_log_scanner.conf
cp $PSC_PATH/conf/pg_stat_log_scanner.conf.example $NEW_CONF_LOG_SCANNER

write_main_db_params()
{
	sed -i "s|MAIN_DB_HOST|$main_db_host|g" $1
	sed -i "s|MAIN_DB_PORT|$main_db_port|g" $1
	sed -i "s|MAIN_DB_NAME|$main_db_name|g" $1
	sed -i "s|MAIN_DB_USER|$main_db_user|g" $1
	sed -i "s|MAIN_DB_PASSW|$main_db_passw|g" $1
}

write_main_db_params $NEW_CONF_STAT_SYS
write_main_db_params $NEW_CONF_LOG_SCANNER

write_node_params()
{
	sed -i "s|PSC_NODE_NAME|$psc_node_name|g" $1
	sed -i "s|PSC_NODE_DESCR|$psc_node_descr|g" $1
	sed -i "s|PSC_NODE_HOST|$psc_node_host|g" $1
	sed -i "s|PSC_TIME_ZONE|$psc_time_zone|g" $1
}

write_node_params $NEW_CONF_STAT_SYS
write_node_params $NEW_CONF_LOG_SCANNER

sed -i "s|PSC_DATABASES_PYPG|$psc_databases_pypg|g" $NEW_CONF_MONITOR
sed -i "s|PG_STAT_MONITOR_PORT|$pg_stat_monitor_port|g" $NEW_CONF_MONITOR
sed -i "s|PG_STAT_MONITOR_ALLOW_HOSTS|$pg_stat_monitor_allow_hosts|g" $NEW_CONF_MONITOR
sed -i "s|PSC_TIME_ZONE|$psc_time_zone|g" $NEW_CONF_MONITOR
sed -i "s|PSC_PG_LOG_DIR|$psc_pg_log_dir|g" $NEW_CONF_MONITOR
sed -i "s|PSC_PG_LOG_DIR|$psc_pg_log_dir|g" $NEW_CONF_LOG_SCANNER

sed -i "s|PSC_DATABASES_PQ|$psc_databases_pq|g" $NEW_CONF_STAT_SYS

if [ "$no_db" == 1 ]; then
	sed -i "s|PSC_COLLECT_DB_STAT|0|g" $NEW_CONF_STAT_SYS
	sed -i "s|PSC_COLLECT_CONN_STAT|0|g" $NEW_CONF_STAT_SYS
else
	sed -i "s|PSC_COLLECT_DB_STAT|1|g" $NEW_CONF_STAT_SYS
	sed -i "s|PSC_COLLECT_CONN_STAT|1|g" $NEW_CONF_STAT_SYS
fi

is_istalled=0

install()
{
	echo -e "\nInstalling pg_stat_console services...\n"
	services=()
	if [ -z $no_pg_stat_monitor ]; then
		services+=("pg_stat_monitor.service")
	fi
	if [ -z $no_pg_stat_sys ]; then
		services+=("pg_stat_sys.service")
	fi
	if [ -z $no_pg_stat_log_scanner ]; then
		services+=("pg_stat_log_scanner.service")
	fi
	source $PSC_PATH/unit/install.sh
	is_istalled=1
}

if [ -z "$psc_install" ]; then
	echo
	echo -n "Install pg_stat_console services to systemctl?"
	echo
	select yn in "Yes" "No"; do
		case $yn in
			Yes ) install; break;;
			No ) break;;
		esac
	done
else
	if [ $psc_install == 1 ] ; then
		install
	fi
fi

source $PSC_PATH/pg_conf.sh

if [ -z "$pg_configure" ]; then
	echo
	echo -n "Configure observed PostgreSQL instance?"
	echo
	select yn in "Yes" "No"; do
		case $yn in
			Yes ) run_pg_configure; break;;
			No ) break;;
		esac
	done
else
	if [[ !($pg_configure == 0) ]] ; then
		run_pg_configure
	fi
fi

run()
{
	echo "Start pg_stat_console services..."
	if [ $is_istalled == 0 ] ; then
		install
	fi
	
	if  [ -z $no_pg_stat_monitor ] && [ -z $pg_stat_monitor_run ]; then
		echo
		echo -n "Run pg_stat_monitor?"
		echo
		select yn in "Yes" "No"; do
			case $yn in
				Yes ) pg_stat_monitor_run=1; break;;
				No ) pg_stat_monitor_run=0; break;;
			esac
		done
	fi
	if  [ -z $no_pg_stat_sys ] && [ -z $pg_stat_sys_run ]; then
		echo
		echo -n "Run pg_stat_sys?"
		echo
		select yn in "Yes" "No"; do
			case $yn in
				Yes ) pg_stat_sys_run=1; break;;
				No ) pg_stat_sys_run=0; break;;
			esac
		done
	fi
	if  [ -z $no_pg_stat_log_scanner ] && [ -z $pg_stat_log_scanner_run ]; then
		echo
		echo -n "Run pg_stat_log_scanner?"
		echo
		select yn in "Yes" "No"; do
			case $yn in
				Yes ) pg_stat_log_scanner_run=1; break;;
				No ) pg_stat_log_scanner_run=0; break;;
			esac
		done
	fi
	
	if [[ $(ps --no-headers -o comm 1) == "systemd" ]]; then
		echo
		if [ -z $no_pg_stat_monitor ] && [ $pg_stat_monitor_run ] && [ $pg_stat_monitor_run == 1 ]; then
			echo "Restarting pg_stat_monitor..."
			systemctl restart pg_stat_monitor
		fi
		if [ -z $no_pg_stat_sys ] && [ $pg_stat_sys_run ] &&  [ $pg_stat_sys_run == 1 ]; then
			echo "Restarting pg_stat_sys..."
			systemctl restart pg_stat_sys
		fi
		if [ -z $no_pg_stat_log_scanner ] && [ $pg_stat_log_scanner_run ] && [ $pg_stat_log_scanner_run == 1 ]; then
			echo "Restarting pg_stat_log_scanner..."
			systemctl restart pg_stat_log_scanner
		fi
	fi
}

if [ -z "$psc_run" ]; then
	echo
	echo -n "Run pg_stat_console services?"
	echo
	select yn in "Yes" "No"; do
		case $yn in
			Yes ) run; break;;
			No ) break;;
		esac
	done
else
	if [ $psc_run == 1 ] ; then
		run
	fi
fi

echo -e "\nDone"