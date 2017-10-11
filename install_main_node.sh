#!/bin/sh

show_help()
{
	echo "---------------------------------------------------"
	echo "--db-host - DB host"
	echo "--db-port - "
	echo "--db-name - "
	echo "--db-user - "
	echo "--db-passw - "
	echo "--psc-admin-passw - "
	echo "---------------------------------------------------"
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
		*)
			echo "ERROR: unknown parameter \"$PARAM\""
			show_help
			exit 1
			;;
	esac
	shift
done

if [ -z "$db_host" ]; then
	echo -n "Enter DB host and press [ENTER] (default 127.0.0.1):"
	read db_host

	if [ -z "$db_host" ]; then
		db_host="127.0.0.1"
		echo "DB host is empty, using $db_host"
	fi
fi

if [ -z "$db_port" ]; then
	echo -n "Enter DB port and press [ENTER] (default 6432):"
	read db_port

	if [ -z "$db_port" ]; then
		db_port="6432"
		echo "DB port is empty, using $db_port"
	fi
fi

if [ -z "$db_name" ]; then
	echo -n "Enter DB name and press [ENTER] (default sys_stat):"
	read db_name

	if [ -z "$db_name" ]; then
		db_name="sys_stat"
		echo "DB name is empty, using '$db_name'"
	fi
fi

if [ -z "$db_user" ]; then
	echo -n "Enter DB user and press [ENTER] (default app_user):"
	read db_user

	if [ -z "$db_user" ]; then
		db_user="app_user"
		echo "DB user is empty, using '$db_user'"
	fi
fi

if [ -z "$db_passw" ]; then
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
	echo -n "Enter pg_stat_console port and press [ENTER] (default 8880):"
	read psc_port
	
	if [ -z "$psc_port" ]; then
		psc_port="8880"
		echo "pg_stat_console port is empty, using '$psc_port'"
	fi
fi

PSC_PATH=$PWD
NEW_CONF=$PSC_PATH/conf/pg_stat_console_new.conf
cp $PSC_PATH/conf/pg_stat_console.conf.example $NEW_CONF

sed -i "s|DB_HOST|$db_host|g" $NEW_CONF
sed -i "s|DB_PORT|$db_port|g" $NEW_CONF
sed -i "s|DB_NAME|$db_name|g" $NEW_CONF
sed -i "s|DB_USER|$db_user|g" $NEW_CONF
sed -i "s|DB_PASSW|$db_passw|g" $NEW_CONF
sed -i "s|PSC_ADMIN_PASSW|$psc_admin_passw|g" $NEW_CONF
sed -i "s|PSC_PORT|$psc_port|g" $NEW_CONF
