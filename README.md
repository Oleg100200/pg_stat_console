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

## Installation

### Recommended settings for postgresql.conf

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
