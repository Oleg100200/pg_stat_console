#!/bin/sh

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

if [[ -z $(yum list installed | grep sysstat) ]]; then
	yum -y install sysstat
else
	echo "sysstat already installed"
fi

if [[ -z $(yum list installed | grep iotop) ]]; then
	yum -y install iotop
else
	echo "iotop already installed"
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
	systemctl_file="/usr/lib/systemd/system/postgresql-10.service"
	cp $systemctl_file ${systemctl_file}.$(date '+%Y%m%d_%H%M%S')
	sed -i "s|Environment=PGDATA=/var/lib/pgsql/10/data/|Environment=PGDATA=$pg_data|g" $systemctl_file
	systemctl daemon-reload
	systemctl restart postgresql-10
}

run_query()
{
	su -l postgres -c "psql -A -t -p 5432 -h 127.0.0.1 -U postgres -d $1 -c \"$2\""
}

execute_file()
{
	su -l postgres -c "psql -A -t -p 5432 -h 127.0.0.1 -U postgres -d $1 -a -f $2"
}

if [ -d "/var/lib/pgsql" ]; then
	echo
	echo 'PostgreSQL already installed'

else
	yum install -y https://download.postgresql.org/pub/repos/yum/10/redhat/rhel-7-x86_64/pgdg-centos10-10-1.noarch.rpm
	yum install -y postgresql10-server postgresql10-contrib
	systemctl enable postgresql-10
	mkdir $pg_data
	chown postgres $pg_data
	su - postgres -c "/usr/pgsql-10/bin/initdb -D $pg_data -E 'UTF-8'"
	allow_port $db_port
	configure_systemctl
	
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

get_scalar()
{
	results=($(su -l postgres -c "psql -A -t -p '${db_port}' -h 127.0.0.1 -U postgres -d $1 -c \"$2\""))
	fld1=`echo ${results[0]} | awk -F'|' '{print $1}'`
	echo ${fld1}
}

pg_config=$(get_scalar "postgres" "select setting from pg_settings where name = 'config_file' limit 1")

echo

strindex() {
  x="${1%%$2*}"
  [[ "$x" = "$1" ]] && echo -1 || echo "${#x}"
}

source $PSC_PATH/pg_conf.sh
run_pg_configure

install_python()
{
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
	if [ ! -f /usr/bin/pgbouncer ]; then
		yum install -y pgbouncer
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
	else
		echo
		echo "pgbouncer already installed"
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
		echo 'DB ${bgbench_db_name} does not exists, creating...'
		run_query "postgres" "$query"

		#execute_file "$PSC_PATH/sql/sys_stat.backup"
	}

	if [ -z "$db_exists" ]
	then
		create_db
	else
		echo 'DB '${bgbench_db_name}' already exists'
	fi
}

configure_pgbench

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