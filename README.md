# pg_stat_console

Collect and display statistics for PostgreSQL server

Live demo of pg_stat_console</br>
User: demo</br>
Passw: demo</br>

http://psc.pg-support.com

## How it works

![Alt text](/img/diagram.png?raw=true "pg_stat_console diagram")

## Dependencies

* Python 3.x with modules: pytz, tornado, sqlalchemy, requests
* PostgreSQL 9.2 or higher with extensions: auto_explain, pg_stat_statements
* OS utils: iotop, iostat, netstat
* RHEL 6, RHEL 7, Ubuntu 12.04 LTS - 16.10

## Roadmap

* online dashboard builder
* dashboard for cluster
* bottleneck assistant
* alerts constructor
* aggregation of old data (compression)
* monthly reports

## Installation (RHEL 7 example)

### OS utils on all nodes

```
yum -y install sysstat iotop git
```

### Clone pg_stat_console on all nodes

```
cd /home
git clone https://github.com/masterlee998/pg_stat_console
```

### Allow ports

On main node you should to allow <code>8888</code> port: 

```
# if firewalld installed
firewall-cmd --zone=public --add-port=8888/tcp --permanent
firewall-cmd --reload

# or
iptables -I INPUT -p tcp -m tcp --dport 8888 -j ACCEPT
iptables-save
```

On observed nodes you should to allow <code>8889</code> port.


### PostgreSQL installation (Main Node)

```
yum install http://yum.postgresql.org/9.6/redhat/rhel-7-x86_64/pgdg-redhat96-9.6-3.noarch.rpm
yum install -y postgresql96-server postgresql96-contrib
systemctl enable postgresql-9.6

mkdir /home/db_main_node
chown postgres /home/db_main_node
su - postgres
/usr/pgsql-9.6/bin/initdb -D /home/db_main_node -E 'UTF-8'

firewall-cmd --zone=public --add-port=5432/tcp --permanent
firewall-cmd --reload
```


### Recommended settings for postgresql.conf on Main Node


```
shared_buffers = 1GB    
temp_buffers = 256MB
work_mem = 256MB                
maintenance_work_mem = 256MB

vacuum_cost_limit = 5000

autovacuum = on
autovacuum_max_workers = 4
autovacuum_naptime = 1min
autovacuum_vacuum_threshold = 10000
autovacuum_analyze_threshold = 5000
autovacuum_vacuum_scale_factor = 0.4
autovacuum_analyze_scale_factor = 0.2
autovacuum_vacuum_cost_delay = 10ms
autovacuum_vacuum_cost_limit = 5000

synchronous_commit = off
checkpoint_timeout = 10min		
max_wal_size = 1GB
min_wal_size = 80MB
checkpoint_completion_target = 0.9	

bgwriter_delay = 5000ms
bgwriter_lru_maxpages = 1000
bgwriter_lru_multiplier = 7.0

stats_temp_directory = '/dev/shm/pg_stat_tmp'

statement_timeout = 3600000            			# in milliseconds, 1 hour
lock_timeout = 600000                       # 10 mins
```

Create directory for <code>stats_temp_directory</code>:

```
mkdir /dev/shm/pg_stat_tmp
chown postgres /dev/shm/pg_stat_tmp
```

Add the directory creation to autorun:

```
chmod +x /etc/rc.d/rc.local
```

<code>nano /etc/rc.d/rc.local</code>:

```
mkdir /dev/shm/pg_stat_tmp
chown postgres /dev/shm/pg_stat_tmp
```

In <code>/usr/lib/systemd/system/postgresql-9.6.service</code> replace:

```
Environment=PGDATA=/var/lib/pgsql/9.6/data/ 
```

to:

```
Environment=PGDATA=/home/db_main_node
```

and then:

```
systemctl daemon-reload
systemctl restart postgresql-9.6
```

Configure DB:

```
su - postgres
/usr/pgsql-9.6/bin/psql -d postgres -p 5432
alter user postgres with password 'postgres';
CREATE ROLE app_user LOGIN password 'app_user' superuser;

CREATE DATABASE sys_stat
  WITH OWNER = app_user
       ENCODING = 'UTF8'
       template=template0
       TABLESPACE = pg_default
       LC_COLLATE = 'en_US.UTF-8'
       LC_CTYPE = 'en_US.UTF-8'
       CONNECTION LIMIT = -1;
```

### Recommended settings for pg_hba.conf on Main Node

<code>nano /home/db_main_node/pg_hba.conf</code>:

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
host    all             app_user        0.0.0.0/0               md5
```

### Restore sys_stat database on Main Node

```
/usr/pgsql-9.6/bin/psql -h localhost -d sys_stat -U postgres -p 5432 -a -f /home/pg_stat_console/sql/sys_stat.backup
```

### pgbouncer configuration on Main Node

pgbouncer should be used to improve performance.

```
yum install pgbouncer
```

<code>nano /etc/pgbouncer/pgbouncer.ini</code>:

```
[databases]
sys_stat = host=127.0.0.1 user=app_user

[pgbouncer]

logfile = /var/log/pgbouncer.log
pidfile = /var/run/pgbouncer/pgbouncer.pid
listen_addr = *
listen_port = 6432

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
```

<code>nano /etc/pgbouncer/userlist.txt</code>:

```
"app_user" "app_user"
```

Run bgbouncer:

```
touch /var/log/pgbouncer.log
chown pgbouncer:pgbouncer /var/log/pgbouncer.log
systemctl restart pgbouncer
systemctl enable pgbouncer
```


### Required settings for postgresql.conf on NodeX

```
shared_preload_libraries = 'pg_stat_statements,auto_explain'
pg_stat_statements.max = 1000
pg_stat_statements.track = all

auto_explain.log_min_duration = '3s'
auto_explain.log_analyze = true
auto_explain.log_verbose = true
auto_explain.log_buffers = true
auto_explain.log_format = text

log_destination = 'csvlog'
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_truncate_on_rotation = on
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_error_statement = error
log_min_duration_statement = 3000
log_duration = off
log_line_prefix = '%t %a'
log_lock_waits = on
log_statement = 'ddl'
log_temp_files = -1
log_timezone = 'Europe/Moscow'

track_activities = on
track_counts = on
track_io_timing = on
track_functions = pl
track_activity_query_size = 2048
```

### Python installation on all nodes

```
yum groupinstall -y 'development tools'
yum install -y zlib-dev openssl-devel sqlite-devel bzip2-devel
wget https://www.python.org/ftp/python/3.6.2/Python-3.6.2.tar.xz
xz -d Python-3.6.2.tar.xz
tar -xvf Python-3.6.2.tar
cd Python-3.6.2
./configure
make && make altinstall
pip3.6 install pytz
pip3.6 install tornado
pip3.6 install sqlalchemy
pip3.6 install requests
```

### pg_stat_console management

To run use:

```
nohup /usr/local/bin/python3.6 /home/pg_stat_console/pg_stat_sys.py > /dev/null 2>&1 &
nohup /usr/local/bin/python3.6 /home/pg_stat_console/pg_stat_monitor.py > /dev/null 2>&1 &
nohup /usr/local/bin/python3.6 /home/pg_stat_console/pg_stat_log_scanner.py > /dev/null 2>&1 &
nohup /usr/local/bin/python3.6 /home/pg_stat_console/pg_stat_console.py > /dev/null 2>&1 &
```

To stop use:

```
ps -ef | grep pg_stat_sys.py | grep -v grep | awk '{print $2}' | xargs kill
ps -ef | grep pg_stat_monitor.py | grep -v grep | awk '{print $2}' | xargs kill
ps -ef | grep pg_stat_log_scanner.py | grep -v grep | awk '{print $2}' | xargs kill
ps -ef | grep pg_stat_console.py | grep -v grep | awk '{print $2}' | xargs kill
```

### pg_stat_console configuration

```
cd /home/pg_stat_console/conf

# on Main Node
mv pg_stat_console.conf.example pg_stat_console.conf

# on NodeX 
mv pg_stat_log_scanner.conf.example pg_stat_log_scanner.conf
mv pg_stat_monitor.conf.example pg_stat_monitor.conf
mv pg_stat_sys.conf.example pg_stat_sys.conf
```

Then open the configuration files <code>conf/*.conf</code> and edit all sections and parameters according to your tasks.

### systemctl configuration

You can install sevice files for all components of pg_stat_console:

```
cd /home/pg_stat_console/units
chmod a+x install.sh
./install.sh

systemctl enable pg_stat_sys
systemctl enable pg_stat_monitor
systemctl enable pg_stat_log_scanner
systemctl enable pg_stat_console

systemctl start pg_stat_sys
systemctl start pg_stat_monitor
systemctl start pg_stat_log_scanner
systemctl start pg_stat_console
```

### Configure pg_stat_statements on NodeX in all observed databases

If observed DB has version 9.2 or 9.3 then use next patch:

```
psql -h localhost -d observed_db_X -U postgres -p 5432 -a -f /home/pg_stat_console/sql/patch_92_pg_stat_statements.sql
```
