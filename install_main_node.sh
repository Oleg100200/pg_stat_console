#!/bin/sh

show_help()
{
	echo
	echo "---------------------------------------------------"
	echo "Parameters"
	echo "---------------------------------------------------"
	echo "--db-host 	- database host"
	echo "--db-port 	- database port"
	echo "--db-name 	- name of database"
	echo "--db-user 	- database user"
	echo "--db-passw 	- database user password"
	echo
	echo "--psc-admin-passw 	- pg_stat_console admin password (other users you can edit in '[users]' section of 'conf/pg_stat_console.conf')"
	echo "--psc-port 		- pg_stat_console web GUI port"
	echo "--psc-time-zone 	- current timezone"
	echo "--psc-monitor-port 	- pg_stat_monitor port"
	echo
	echo "--psc-create-db/psc-no-create-db 	- create database if not exists or not"
	echo "--psc-install/psc-no-install 		- install pg_stat_console service or not"
	echo "--psc-run/psc-no-run 			- run pg_stat_console service (web GUI) or not"

	echo '
---------------------------------------------------
Usage
---------------------------------------------------
chmod +x install_main_node.sh

./install_main_node.sh

	OR

./install_main_node.sh --db-host=127.0.0.1 --db-port=5432 --db-name=sys_stat_test \
--db-user=app_user --db-passw=app_user --psc-admin-passw=passw --psc-port=8888 \
--psc-time-zone="Europe/Moscow" --psc-monitor-port=8889 --psc-create-db --psc-install --psc-run

	OR

./install_main_node.sh --psc-no-create-db --psc-no-install --psc-no-run
'
}

while [ "$1" != "" ]; do
	PARAM=`echo $1 | awk -F= '{print $1}'`
	VALUE=`echo $1 | awk -F= '{print $2}'`
	case $PARAM in
		-h | --help)
			show_help
			exit
			;;
		--db-host)
			db_host=$VALUE
			;;
		--db-port)
			db_port=$VALUE
			;;
		--db-name)
			db_name=$VALUE
			;;
		--db-user)
			db_user=$VALUE
			;;
		--db-passw)
			db_passw=$VALUE
			;;
		--psc-admin-passw)
			psc_admin_passw=$VALUE
			;;
		--psc-port)
			psc_port=$VALUE
			;;
		--psc-time-zone)
			psc_time_zone=$VALUE
			;;
		--psc-monitor-port)
			psc_monitor_port=$VALUE
			;;
		--psc-create-db)
			psc_create_db=1
			;;			
		--psc-install)
			psc_install=1
			;;
		--psc-run)
			psc_run=1
			;;
		--psc-no-create-db)
			psc_create_db=0
			;;			
		--psc-no-install)
			psc_install=0
			;;
		--psc-no-run)
			psc_run=0
			;;	
		*)
			echo "ERROR: unknown parameter \"$PARAM\""
			show_help
			exit 1
			;;
	esac
	shift
done

if [[ !(-z $(ps -ef | grep pg_stat_console.py | grep -v grep | awk '{print $2}')) ]]; then
	echo "pg_stat_console already runned"
	exit
fi

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

if [ -z "$db_name" ]; then
	echo
	echo -n "Enter DB name and press [ENTER] (default sys_stat):"
	read db_name

	if [ -z "$db_name" ]; then
		db_name="sys_stat"
		echo "DB name is empty, using '$db_name'"
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

if [ -z "$psc_admin_passw" ]; then
	echo
	echo -n "Enter pg_stat_console admin password and press [ENTER] (default admin):"
	stty -echo
	read psc_admin_passw; echo
	stty echo
	
	if [ -z "$psc_admin_passw" ]; then
		psc_admin_passw="admin"
		echo "pg_stat_console admin password is empty, using '$psc_admin_passw'"
	fi
fi

if [ -z "$psc_port" ]; then
	echo
	echo -n "Enter pg_stat_console port and press [ENTER] (default 8880):"
	read psc_port
	
	if [ -z "$psc_port" ]; then
		psc_port="8880"
		echo "pg_stat_console port is empty, using '$psc_port'"
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

if [ -z "$psc_monitor_port" ]; then
	echo
	echo -n "Enter pg_stat_monitor port (default 8889):"
	read psc_monitor_port
	
	if [ -z "$psc_monitor_port" ]; then
		psc_monitor_port="8889"
		echo "pg_stat_monitor port is empty, using '$psc_monitor_port'"
	fi
fi

PSC_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
NEW_CONF=$PSC_PATH/conf/pg_stat_console.conf
cp $PSC_PATH/conf/pg_stat_console.conf.example $NEW_CONF

sed -i "s|DB_HOST|$db_host|g" $NEW_CONF
sed -i "s|DB_PORT|$db_port|g" $NEW_CONF
sed -i "s|DB_NAME|$db_name|g" $NEW_CONF
sed -i "s|DB_USER|$db_user|g" $NEW_CONF
sed -i "s|DB_PASSW|$db_passw|g" $NEW_CONF
sed -i "s|PSC_ADMIN_PASSW|$psc_admin_passw|g" $NEW_CONF
sed -i "s|PSC_PORT|$psc_port|g" $NEW_CONF
sed -i "s|PSC_TIME_ZONE|$psc_time_zone|g" $NEW_CONF
sed -i "s|PSC_MONITOR_PORT|$psc_monitor_port|g" $NEW_CONF

get_scalar()
{
	results=($(su -l postgres -c "PGPASSWORD='${db_passw}'; psql -A -t -p '${db_port}' -h '${db_host}' -U '${db_user}' -d $1 -c \"$2\""))
	fld1=`echo ${results[0]} | awk -F'|' '{print $1}'`
	echo ${fld1}
}

execute_file()
{
	su -l postgres -c "PGPASSWORD='${db_passw}'; psql -A -t -p '${db_port}' -h '${db_host}' -U '${db_user}' -d '${db_name}' -a -f $1"
}

run_query()
{
	su -l postgres -c "PGPASSWORD='${db_passw}'; psql -A -t -p '${db_port}' -h '${db_host}' -U '${db_user}' -d $1 -c \"$2\""
}

db_exists=$(get_scalar "postgres" "SELECT datname FROM pg_database WHERE datname='${db_name}' limit 1")


create_db()
{
	if [ -z "$db_exists" ]
	then
		query="
			CREATE DATABASE ${db_name}
				WITH OWNER = ${db_user}
				ENCODING = 'UTF8'
				template=template0
				TABLESPACE = pg_default
				LC_COLLATE = 'en_US.UTF-8'
				LC_CTYPE = 'en_US.UTF-8'
				CONNECTION LIMIT = -1;
		"
		echo 'DB does not exists, creating...'
		run_query "postgres" "$query"
		execute_file "$PSC_PATH/sql/sys_stat.backup"
	else
	  echo 'DB already exists'
	fi
	echo
}

if [ -z "$db_exists" ]
then
	if [ -z "$psc_create_db" ]; then
		echo
		echo -n "Create DB for pg_stat_console?"
		echo
		select yn in "Yes" "No"; do
			case $yn in
				Yes ) create_db; break;;
				No ) break;;
			esac
		done
	else
		if [ $psc_create_db == 1 ] ; then
			create_db
		fi
	fi
fi

is_istalled=0

install()
{
	echo -e "\nInstalling pg_stat_console service...\n"
	services=(pg_stat_console.service)
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

run()
{
	echo "Start pg_stat_console service..."
	if [ $is_istalled == 0 ] ; then
		install
	fi
	
	if [[ $(ps --no-headers -o comm 1) == "systemd" ]]; then
		systemctl restart pg_stat_console
	else
		service pg_stat_console restart
	fi
}

if [ -z "$psc_run" ]; then
	echo
	echo -n "Run pg_stat_console service?"
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