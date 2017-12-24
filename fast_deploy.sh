#!/bin/bash

psc_port=8888
psc_monitor_port=8889
psc_admin_passw="admin"
pg_data="/home/db_main_node"

db_port=5432
db_name="sys_stat"
db_user="app_user"
db_user_passw=$db_user
pgbouncer_port=6432
bgbench_db_name="test_db"

PSC_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $PSC_PATH/pg_conf.sh

pg_version=0
pg_service_name=""
pg_dir_bin=""
current_os=""
ubuntu_release=""

if [ -f /etc/redhat-release ]; then
  current_os="RHEL"
fi

if [ -f /etc/lsb-release ]; then
	current_os="Ubuntu"

	if [[ $(lsb_release -d | gawk -F"\t" '{print $2}') == *"Ubuntu 17."* ]]; then
		ubuntu_release="zesty"
	fi
	if [[ $(lsb_release -d | gawk -F"\t" '{print $2}') == *"Ubuntu 16."* ]]; then
		ubuntu_release="xenial"
	fi
	if [[ $(lsb_release -d | gawk -F"\t" '{print $2}') == *"Ubuntu 14."* ]]; then
		ubuntu_release="trusty"
	fi
fi

show_help()
{
	echo
	echo "---------------------------------------------------"
	echo "Parameters"
	echo "---------------------------------------------------"
	echo "--force 	- do not ask questions"
	echo "--no-configure-pgbench	- do not configure pgbench"
	echo
}

while [ "$1" != "" ]; do
	PARAM=`echo $1 | awk -F= '{print $1}'`
	VALUE=`echo $1 | awk -F= '{print $2}'`
	case $PARAM in
		-h | --help)
			show_help
			exit
			;;
		--force)
			force=1
			;;
		--no-configure-pgbench)
			no_configure_pgbench=1
			;;
		*)
			echo "ERROR: unknown parameter \"$PARAM\""
			show_help
			exit 1
			;;
	esac
	shift
done

if [ ! "$force" ]; then
	echo
	echo -e "This script will install PostgreSQL and environment (python, pgbouncer), "
	echo -e "as well as automatically configure pg_stat_console and run it."
	echo -e "WARNING: don't use this script on production systems. Continue?"
	echo
	select yn in "Yes" "No"; do
		case $yn in
			Yes ) break;;
			No ) exit;;
		esac
	done
fi

echo -e "----------------------------------"

if [ $current_os == "RHEL" ]; then
	if [[ -z $(yum list installed | grep sysstat) ]]; then
		yum -y install sysstat
	else
		echo "sysstat already installed"
	fi
fi
	
if [ $current_os == "Ubuntu" ]; then
	if [[ -z $(dpkg-query --list | grep sysstat) ]]; then
		apt-get -y install sysstat
	else
		echo "sysstat already installed"
	fi
fi

if [ $current_os == "RHEL" ]; then
	if [[ -z $(yum list installed | grep iotop) ]]; then
		yum -y install iotop
	else
		echo "iotop already installed"
	fi
fi

if [ $current_os == "Ubuntu" ]; then
	if [[ -z $(dpkg-query --list | grep iotop) ]]; then
		apt-get -y install iotop
	else
		echo "iotop already installed"
	fi
fi

allow_port()
{
	if [[ -z $(iptables -nL | grep "$1") ]]; then
		echo "Allowing '$1' port..."
		iptables-save -c > /etc/iptables-backup_$(date '+%Y%m%d_%H%M%S') #for restore use: iptables-restore -c < iptables-backup_*
		iptables -I INPUT -p tcp -m tcp --dport $1 -j ACCEPT
		iptables-save >/dev/null
	else
		echo "Port '$1' already allowed"
	fi
}

allow_port $psc_port

configure_systemctl()
{
	if [ $current_os == "RHEL" ]; then
		systemctl_file="/usr/lib/systemd/system/postgresql-10.service"
		cp $systemctl_file ${systemctl_file}.$(date '+%Y%m%d_%H%M%S')
		sed -i "s|Environment=PGDATA=/var/lib/pgsql/10/data/|Environment=PGDATA=$pg_data|g" $systemctl_file
		systemctl daemon-reload
		systemctl restart postgresql-10
	fi
}

run_query()
{
	su -l postgres -c "psql -A -t -p ${db_port} -U postgres -d $1 -c \"$2\""
}

execute_file()
{
	su -l postgres -c "psql -A -t -p ${db_port} -U postgres -d $1 -a -f $2"
}

get_scalar()
{
	results=($(su -l postgres -c "psql -A -t -p '${db_port}' -U postgres -d $1 -c \"$2\""))
	fld1=`echo ${results[0]} | awk -F'|' '{print $1}'`
	echo ${fld1}
}

if [ -d "/var/lib/pgsql" ] || [ -d "/var/lib/postgresql" ]; then
	echo
	#here we suppose that systemctl already configured and initdb executed
	get_pg_version			#from $PSC_PATH/pg_conf.sh
	run_pg_configure		#from $PSC_PATH/pg_conf.sh
	echo $pg_service_name' already installed'
	
	role_exists=$(get_scalar "postgres" "select 1 from pg_user where usename = '${db_user}' limit 1")
	
	if [ -z "$role_exists" ]
	then
		query_create_role="CREATE ROLE ${db_user} LOGIN password '${db_user_passw}' superuser;"
		run_query "postgres" "$query_create_role"
	else
		echo 'ROLE '${db_user}' already exists'
	fi
	
	db_exists=$(get_scalar "postgres" "SELECT datname FROM pg_database WHERE datname='${db_name}' limit 1")

	create_db()
	{
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
		echo 'DB "${db_name}" does not exists, creating...'
		run_query "postgres" "$query"
	}

	if [ -z "$db_exists" ]
	then
		create_db
		echo 'DB '${db_name}' is created'
	else
		echo 'DB '${db_name}' already exists'
	fi

	sys_stat_objs_exists=$(get_scalar "${db_name}" "select 1 from pg_class where relname = 'psc_nodes' and relkind = 'r' limit 1")
	if [ -z "$sys_stat_objs_exists" ]
	then
		execute_file "$db_name" "$PSC_PATH/sql/sys_stat.backup"
	else
		echo 'DB '${db_name}' already restored'
	fi
	
else

	if [ $current_os == "RHEL" ]; then
		yum install -y https://download.postgresql.org/pub/repos/yum/10/redhat/rhel-7-x86_64/pgdg-centos10-10-1.noarch.rpm
		yum install -y postgresql10-server postgresql10-contrib
	fi

	if [ $current_os == "Ubuntu" ]; then
		cat > /etc/apt/sources.list.d/pgdg.list << EOL
deb http://apt.postgresql.org/pub/repos/apt/ $ubuntu_release-pgdg main
EOL

		wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
		  sudo apt-key add -
		sudo apt-get update
		apt-get install -y postgresql postgresql-contrib
	fi
	
	systemctl enable postgresql-10
	mkdir $pg_data
	chown postgres $pg_data

	if [ $current_os == "RHEL" ]; then
		su - postgres -c "/usr/pgsql-10/bin/initdb -D $pg_data -E 'UTF-8'"
	fi
	if [ $current_os == "Ubuntu" ]; then
		su - postgres -c "/usr/lib/postgresql/10/bin/initdb -D $pg_data -E 'UTF-8'"
	fi

	allow_port $db_port
	configure_systemctl
	get_pg_version			#from $PSC_PATH/pg_conf.sh
	run_pg_configure		#from $PSC_PATH/pg_conf.sh

	query_create_role="
	alter user postgres with password 'postgres';
	CREATE ROLE ${db_user} LOGIN password '${db_user_passw}' superuser;"

	run_query "postgres" "$query_create_role"

	query="
		CREATE DATABASE ${db_name}
			WITH OWNER = ${db_user}
			ENCODING = 'UTF8'
			template=template0
			TABLESPACE = pg_default
			LC_COLLATE = 'en_US.UTF-8'
			LC_CTYPE = 'en_US.UTF-8'
			CONNECTION LIMIT = -1;"

	run_query "postgres" "$query"
	execute_file "$db_name" "$PSC_PATH/sql/sys_stat.backup"
fi

echo

install_python()
{
	if [ $current_os == "RHEL" ]; then
		if [ ! -f /usr/local/bin/python3.6 ]; then
			yum groupinstall -y 'development tools'
			yum install -y zlib-dev openssl-devel sqlite-devel bzip2-devel
			wget https://www.python.org/ftp/python/3.6.2/Python-3.6.2.tar.xz
			xz -d Python-3.6.2.tar.xz
			tar -xvf Python-3.6.2.tar
			cd Python-3.6.2
			./configure
			make && make altinstall
		else
			echo "Python already installed"
		fi
	fi
	
	if [ $current_os == "Ubuntu" ]; then
		if [ ! -f /usr/bin/python3.6 ]; then
			apt-get install -y python3.6
			curl https://bootstrap.pypa.io/get-pip.py | sudo python3.6
		else
			echo "Python already installed"
		fi
	fi

	if [ $current_os == "Ubuntu" ] && [ ! -f /usr/local/bin/pip3.6 ]; then
		curl https://bootstrap.pypa.io/get-pip.py | sudo python3.6
	fi

	if [[ -z $(pip3.6 list --format columns | grep pytz) ]]; then
		pip3.6 install pytz
	fi
	if [[ -z $(pip3.6 list --format columns | grep tornado) ]]; then
		pip3.6 install tornado
	fi	
	if [[ -z $(pip3.6 list --format columns | grep SQLAlchemy) ]]; then
		pip3.6 install sqlalchemy
	fi
	if [[ -z $(pip3.6 list --format columns | grep requests) ]]; then
		pip3.6 install requests
	fi
}

install_python 

install_pgbouncer()
{
	if [ -f /usr/bin/pgbouncer ] || [ -f /usr/local/bin/pgbouncer ]; then
		echo
		echo "pgbouncer already installed"
	else
	if [ $current_os == "RHEL" ]; then
		yum install -y pgbouncer
		systemctl enable pgbouncer
	fi
	
	if [ $current_os == "Ubuntu" ]; then
		apt-get install -y build-essential libtool m4 automake
		apt-get install -y libevent-dev libc-ares2 \
		libc-ares-dev \
		libev4 \
		libev-dev \
		libevent-dev \
		libssl1.0.0 \
		libssl-dev \
		libtool \
		pkg-config \
		python-docutils

		git clone https://github.com/pgbouncer/pgbouncer.git
		cd pgbouncer
		git submodule init
		git submodule update
		./autogen.sh
		./configure
		make
		make install
		mkdir /etc/pgbouncer
		cd ..
		mv pgbouncer/etc/* /etc/pgbouncer/
		
		groupadd -r pgbouncer
		useradd -rm -d /var/run/pgbouncer -g pgbouncer pgbouncer
		chown pgbouncer:pgbouncer /etc/pgbouncer/*
		cat > /etc/systemd/system/pgbouncer.service << EOL
[Unit]
Description=A lightweight connection pooler for PostgreSQL
After=syslog.target
After=network.target

[Service]
Type=forking

User=pgbouncer
Group=pgbouncer

Environment=BOUNCERCONF=/etc/pgbouncer/pgbouncer.ini

PIDFile=/var/run/pgbouncer/pgbouncer.pid

ExecStart=/usr/local/bin/pgbouncer -d -q \${BOUNCERCONF}
ExecReload=/usr/bin/kill -HUP \$MAINPID
KillSignal=SIGINT

TimeoutSec=300

[Install]
WantedBy=multi-user.target
EOL
		systemctl daemon-reload
	fi

		cat > /etc/pgbouncer/pgbouncer.ini << EOL
[databases]
${db_name} = host=127.0.0.1 user=${db_user}
${bgbench_db_name} = host=127.0.0.1 user=${db_user}

[pgbouncer]

logfile = /var/log/pgbouncer.log
pidfile = /var/run/pgbouncer/pgbouncer.pid
listen_addr = 127.0.0.1
listen_port = ${pgbouncer_port}

auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

admin_users = postgres
stats_users = stats, postgres

pool_mode = session
server_reset_query = DISCARD ALL
max_client_conn = 600
default_pool_size = 150
reserve_pool_size = 50

ignore_startup_parameters = extra_float_digits,client_min_messages

server_lifetime = 10800
server_idle_timeout = 1200

client_idle_timeout = 3600
query_wait_timeout = 14400
idle_transaction_timeout = 3600

log_connections = 0
log_disconnections = 0
log_pooler_errors = 1
EOL

	cat > /etc/pgbouncer/userlist.txt << EOL
"${db_user}" "${db_user_passw}"
EOL

		touch /var/log/pgbouncer.log
		chown pgbouncer:pgbouncer /var/log/pgbouncer.log
		systemctl restart pgbouncer
		systemctl enable pgbouncer
	fi
}

install_pgbouncer

configure_pgbench()
{
	db_exists=$(get_scalar "postgres" "SELECT datname FROM pg_database WHERE datname='${bgbench_db_name}' limit 1")

	create_db()
	{
		query="
			CREATE DATABASE ${bgbench_db_name}
				WITH OWNER = ${db_user}
				ENCODING = 'UTF8'
				template=template0
				TABLESPACE = pg_default
				LC_COLLATE = 'en_US.UTF-8'
				LC_CTYPE = 'en_US.UTF-8'
				CONNECTION LIMIT = -1;
		"
		echo 'DB '${bgbench_db_name}' does not exists, creating...'
		run_query "postgres" "$query"

		su - postgres -c "${pg_dir_bin}/pgbench -i ${bgbench_db_name} -p ${db_port} --foreign-keys"
	}

	if [ -z "$db_exists" ]
	then
		create_db
		crontab -l > $PSC_PATH/tmp_cron
		echo "*/3 * * * * su - postgres -c \"${pg_dir_bin}/pgbench ${bgbench_db_name} -p ${db_port} -t 3000 --no-vacuum\" >> $PSC_PATH/log/cron_pgbench.log 2>&1" >> $PSC_PATH/tmp_cron
		crontab $PSC_PATH/tmp_cron
	else
		echo 'DB '${bgbench_db_name}' already exists'
	fi
}

if [ ! "$no_configure_pgbench" ]; then
	configure_pgbench
fi

./install_main_node.sh --db-host=127.0.0.1 --db-port=$db_port --db-name=$db_name \
--db-user=$db_user --db-passw=$db_user_passw --psc-admin-passw=$psc_admin_passw --psc-port=$psc_port \
--psc-time-zone="Europe/Moscow" --psc-monitor-port=$psc_monitor_port --psc-no-create-db --psc-install --psc-run

./install_observed_node.sh \
--main-db-host=127.0.0.1 --main-db-port=$pgbouncer_port --main-db-name=$db_name --main-db-user=$db_user --main-db-passw=$db_user_passw \
--db-host=127.0.0.1 --db-port=$pgbouncer_port --db-names=$bgbench_db_name --db-user=$db_user --db-passw=$db_user_passw \
--pg-no-configure \
--psc-time-zone="Europe/Moscow" --pg-stat-monitor-port=$psc_monitor_port --pg-stat-monitor-allow-hosts="127.0.0.1" \
--psc-node-name="my node" --psc-node-descr="node descr" --psc-node-host="127.0.0.1" --psc-install \
--psc-pg-log-dir="/var/log/pg_log" --psc-run --pg-stat-monitor-run --pg-stat-sys-run --pg-stat-log-scanner-run

echo -e "\nDeploy is done"
echo -e "----------------------------------"
echo -e "pg_stat_console is ready to use: http://127.0.0.1:${psc_port}"
echo -e "Login: admin"
echo -e "Password: ${psc_admin_passw}"
echo
echo -e "After 10 minutes, the datapoints will appear on the graphs..."
echo -e "----------------------------------"