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

### OS utils

```
yum -y install sysstat iotop
```

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


### Recommended settings for postgresql.conf of Main Node


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
autovacuum_freeze_max_age = 800000000
autovacuum_vacuum_cost_delay = 10ms
autovacuum_vacuum_cost_limit = 5000

checkpoint_timeout = 10min		
max_wal_size = 1GB
min_wal_size = 80MB
checkpoint_completion_target = 0.9	

bgwriter_delay = 5000ms
bgwriter_lru_maxpages = 1000
bgwriter_lru_multiplier = 7.0

stats_temp_directory = '/dev/shm/pg_stat_tmp'

statement_timeout = 3600000            			# in milliseconds, 1 hour
lock_timeout = 600000                       #10 mins
```

Create directory for <code>stats_temp_directory</code>:

```
mkdir /dev/shm/pg_stat_tmp
chown postgres /dev/shm/pg_stat_tmp
```



### Required settings for postgresql.conf of NodeX

```
shared_preload_libraries = 'pg_stat_statements,auto_explain'
pg_stat_statements.max = 10000
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

### Python installation

```
yum groupinstall -y 'development tools'
yum install -y zlib-dev openssl-devel sqlite-devel bzip2-devel
wget https://www.python.org/ftp/python/3.6.1/Python-3.6.1.tar.xz
xz -d Python-3.6.1.tar.xz
tar -xvf Python-3.6.1.tar
cd Python-3.6.1
./configure
make && make altinstall
pip3.6 install pytz
pip3.6 install tornado
pip3.6 install sqlalchemy
pip3.6 install requests
```

