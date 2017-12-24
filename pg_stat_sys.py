from threading import Thread
import threading
import postgresql
import sys
from datetime import datetime, timedelta
import os
import re
import time
import configparser 
import locale
import subprocess
from distutils.version import LooseVersion
from pgstatlogger import PSCLogger
from pgstatcommon.pg_stat_common import *
#=======================================================================================================
current_dir = os.path.dirname(os.path.realpath(__file__)) + '/'
prepare_dirs(current_dir)
#=======================================================================================================
#init config
config = configparser.RawConfigParser()
config.optionxform = lambda option: option
config.read( current_dir + 'conf/pg_stat_sys.conf')
#=======================================================================================================
#vars from config
sys_stat_conn_str = read_conf_param_value( config['sys_stat']['sys_stat'] )
application_name = read_conf_param_value( config['main']['application_name'] )
sleep_interval_on_exception= int( read_conf_param_value( config['main']['sleep_interval_on_exception'] ) )
sleep_interval_os_stat = read_conf_param_value( config['main']['sleep_interval_os_stat'] )
sleep_interval_pg_sys_stat = int( read_conf_param_value( config['main']['sleep_interval_pg_sys_stat'] ) )
sleep_interval_os_stat_if_iostat_not_working = int( read_conf_param_value( config['main']['sleep_interval_os_stat_if_iostat_not_working'] ) )
time_zone = read_conf_param_value( config['main']['time_zone'] )

dbs_list = []
for db in config['databases']:
	dbs_list.append( [db, read_conf_param_value( config['databases'][db] ) ] )

node_name = read_conf_param_value( config['main']['node_name'] )
node_descr = read_conf_param_value( config['main']['node_descr'] )
node_host = read_conf_param_value( config['main']['node_host'] )

top_rels_in_snapshot = read_conf_param_value( config['main']['top_rels_in_snapshot'] )
top_stm_queries_in_snapshot = read_conf_param_value( config['main']['top_stm_queries_in_snapshot'] )
locks_limit_in_snapshot = read_conf_param_value( config['main']['locks_limit_in_snapshot'] )
sleep_interval_pg_conn_snapshot = int( read_conf_param_value( config['main']['sleep_interval_pg_conn_snapshot'] ) )
sleep_interval_pg_single_db_sn = int( read_conf_param_value( config['main']['sleep_interval_pg_single_db_sn'] ) )
pg_single_db_sn_steps = int( read_conf_param_value( config['main']['pg_single_db_sn_steps'] ) )

collect_pg_sys_stat = read_conf_param_value( config['main']['collect_pg_sys_stat'], True )
collect_pg_conn_snapshot = read_conf_param_value( config['main']['collect_pg_conn_snapshot'], True )
collect_os_stat = read_conf_param_value( config['main']['collect_os_stat'], True )
#=======================================================================================================
create_lock( current_dir, application_name )
#=======================================================================================================
logger = PSCLogger( application_name )
logger.start()
#=======================================================================================================
exclude_tables = """'public.psc_stat_bgwriter_t2', 'public.psc_stat_bgwriter_t1', 'public.psc_stat_dbs_t2', 
					   'public.psc_stat_dbs_t1', 'public.psc_data_t1', 'public.psc_data_io_t1', 'public.psc_data_all_indexes_t1', 
					   'public.psc_data_t2', 'public.psc_data_io_t2', 'public.psc_data_all_indexes_t2',
					   'public.psc_stm_t1', 'public.psc_stm_t2'"""
#=======================================================================================================
query_check_tables_all_dbs = """do $$ 
	begin

	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_data_all_indexes_t1'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN

		CREATE UNLOGGED TABLE psc_data_all_indexes_t1
		(
		  now timestamp with time zone,
		  indexrelid oid,
		  relname text,
		  idx_scan bigint,
		  idx_tup_read bigint,
		  idx_tup_fetch bigint
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;
		
	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_data_all_indexes_t2'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN	  
		CREATE UNLOGGED TABLE psc_data_all_indexes_t2
		(
		  now timestamp with time zone,
		  indexrelid oid,
		  relname text,
		  idx_scan bigint,
		  idx_tup_read bigint,
		  idx_tup_fetch bigint
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;

	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_data_io_t1'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN	  
		CREATE UNLOGGED TABLE psc_data_io_t1
		(
		  now timestamp with time zone,
		  relid oid,
		  relname text,
		  heap_blks_read bigint,
		  idx_blks_read bigint
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;

	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_data_io_t2'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN	 
		CREATE UNLOGGED TABLE psc_data_io_t2
		(
		  now timestamp with time zone,
		  relid oid,
		  relname text,
		  heap_blks_read bigint,
		  idx_blks_read bigint
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;

	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_data_t1'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN	 
		CREATE UNLOGGED TABLE psc_data_t1
		(
		  now timestamp with time zone,
		  relid oid,
		  relname text,
		  seq_scan bigint,
		  seq_tup_read bigint,
		  idx_scan bigint,
		  idx_tup_fetch bigint,
		  n_tup_ins bigint, 
		  n_tup_upd bigint, 
		  n_tup_del bigint, 
		  n_tup_hot_upd bigint
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;

	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_data_t2'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN		  
		CREATE UNLOGGED TABLE psc_data_t2
		(
		  now timestamp with time zone,
		  relid oid,
		  relname text,
		  seq_scan bigint,
		  seq_tup_read bigint,
		  idx_scan bigint,
		  idx_tup_fetch bigint,
		  n_tup_ins bigint, 
		  n_tup_upd bigint, 
		  n_tup_del bigint, 
		  n_tup_hot_upd bigint
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;

	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_stm_t1'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN	 
		CREATE UNLOGGED TABLE psc_stm_t1
		(
		  now timestamp with time zone,
		  userid oid,
		  dbid oid,
		  queryid bigint,
		  query text,
		  calls bigint,
		  total_time double precision,
		  rows bigint,
		  shared_blks_hit bigint,
		  shared_blks_read bigint,
		  shared_blks_dirtied bigint,
		  shared_blks_written bigint,
		  local_blks_hit bigint,
		  local_blks_read bigint,
		  local_blks_dirtied bigint,
		  local_blks_written bigint,
		  temp_blks_read bigint,
		  temp_blks_written bigint,
		  blk_read_time double precision,
		  blk_write_time double precision
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;

	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_stm_t2'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN		  
		CREATE UNLOGGED TABLE psc_stm_t2
		(
		  now timestamp with time zone,
		  userid oid,
		  dbid oid,
		  queryid bigint,
		  query text,
		  calls bigint,
		  total_time double precision,
		  rows bigint,
		  shared_blks_hit bigint,
		  shared_blks_read bigint,
		  shared_blks_dirtied bigint,
		  shared_blks_written bigint,
		  local_blks_hit bigint,
		  local_blks_read bigint,
		  local_blks_dirtied bigint,
		  local_blks_written bigint,
		  temp_blks_read bigint,
		  temp_blks_written bigint,
		  blk_read_time double precision,
		  blk_write_time double precision
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;

	IF not EXISTS (
		select 1 
		from pg_extension 
		where extname = 'pg_stat_statements'
	 ) THEN		  
		create extension if not exists pg_stat_statements;
	END IF;

	end$$;"""

query_all_dbs_t1 = """
	do $$ 
	begin
		delete from psc_data_t1;
		insert into psc_data_t1 select now(),relid, (schemaname||'.'||relname) as relname, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch, n_tup_ins, n_tup_upd, n_tup_del, n_tup_hot_upd from pg_stat_all_tables;
		delete from psc_data_io_t1;
		insert into psc_data_io_t1 select now(),relid, (schemaname||'.'||relname) as relname, heap_blks_read, idx_blks_read from pg_statio_all_tables;
		delete from psc_data_all_indexes_t1;
		insert into psc_data_all_indexes_t1 select now(),indexrelid, (schemaname||'.'||relname||'.'||indexrelname) as relname, idx_scan, idx_tup_read, idx_tup_fetch from pg_stat_all_indexes;
		delete from psc_stm_t1;
		INSERT INTO psc_stm_t1(
					now, userid, dbid, queryid, query, calls, total_time, rows, shared_blks_hit, 
					shared_blks_read, shared_blks_dirtied, shared_blks_written, local_blks_hit, 
					local_blks_read, local_blks_dirtied, local_blks_written, temp_blks_read, 
					temp_blks_written, blk_read_time, blk_write_time)
		SELECT now(), userid, dbid, queryid, query, calls, total_time, rows, shared_blks_hit, 
					shared_blks_read, shared_blks_dirtied, shared_blks_written, local_blks_hit, 
					local_blks_read, local_blks_dirtied, local_blks_written, temp_blks_read, 
					temp_blks_written, blk_read_time, blk_write_time 
		from public.pg_stat_statements(true) where dbid = (select oid from pg_database where datname = current_database());
	end$$;""";

query_all_dbs_t2 = """
	do $$ 
	begin
		delete from psc_data_t2;
		insert into psc_data_t2 select now(),relid, (schemaname||'.'||relname) as relname, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch, n_tup_ins, n_tup_upd, n_tup_del, n_tup_hot_upd from pg_stat_all_tables;
		delete from psc_data_io_t2;
		insert into psc_data_io_t2 select now(),relid, (schemaname||'.'||relname) as relname, heap_blks_read, idx_blks_read from pg_statio_all_tables;
		delete from psc_data_all_indexes_t2;
		insert into psc_data_all_indexes_t2 select now(),indexrelid, (schemaname||'.'||relname||'.'||indexrelname) as relname, idx_scan, idx_tup_read, idx_tup_fetch from pg_stat_all_indexes;
		delete from psc_stm_t2;
		INSERT INTO psc_stm_t2(
					now, userid, dbid, queryid, query, calls, total_time, rows, shared_blks_hit, 
					shared_blks_read, shared_blks_dirtied, shared_blks_written, local_blks_hit, 
					local_blks_read, local_blks_dirtied, local_blks_written, temp_blks_read, 
					temp_blks_written, blk_read_time, blk_write_time)
		SELECT now(), userid, dbid, queryid, query, calls, total_time, rows, shared_blks_hit, 
					shared_blks_read, shared_blks_dirtied, shared_blks_written, local_blks_hit, 
					local_blks_read, local_blks_dirtied, local_blks_written, temp_blks_read, 
					temp_blks_written, blk_read_time, blk_write_time 
		from public.pg_stat_statements(true) where dbid = (select oid from pg_database where datname = current_database());
	end$$;""";

query_check_tables_single_db = """
	do $$ 
	begin

	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_stat_bgwriter_t2'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN

		CREATE UNLOGGED TABLE public.psc_stat_bgwriter_t2
		(
		  now timestamp with time zone,
		  checkpoints_timed bigint,
		  checkpoints_req bigint,
		  checkpoint_write_time bigint,
		  checkpoint_sync_time bigint,
		  buffers_checkpoint bigint,
		  buffers_clean bigint,
		  maxwritten_clean bigint,
		  buffers_backend bigint,
		  buffers_alloc bigint,
		  buffers_backend_fsync bigint
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;
	
	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_stat_bgwriter_t1'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN

		CREATE UNLOGGED TABLE public.psc_stat_bgwriter_t1
		(
		  now timestamp with time zone,
		  checkpoints_timed bigint,
		  checkpoints_req bigint,
		  checkpoint_write_time bigint,
		  checkpoint_sync_time bigint,
		  buffers_checkpoint bigint,
		  buffers_clean bigint,
		  maxwritten_clean bigint,
		  buffers_backend bigint,
		  buffers_alloc bigint,
		  buffers_backend_fsync bigint
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;	
	
	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_stat_dbs_t1'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN

		CREATE UNLOGGED TABLE public.psc_stat_dbs_t1
		(
		  now timestamp with time zone,
		  datid oid,
		  datname text,
		  numbackends integer,
		  xact_commit bigint,
		  xact_rollback bigint,
		  blks_read bigint,
		  blks_hit bigint,
		  tup_returned bigint,
		  tup_fetched bigint,
		  tup_inserted bigint,
		  tup_updated bigint,
		  tup_deleted bigint,
		  deadlocks bigint,
		  temp_files bigint,
		  temp_bytes bigint,
		  blk_read_time bigint,
		  blk_write_time bigint
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;	

	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_stat_dbs_t2'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN

		CREATE UNLOGGED TABLE public.psc_stat_dbs_t2
		(
		  now timestamp with time zone,
		  datid oid,
		  datname text,
		  numbackends integer,
		  xact_commit bigint,
		  xact_rollback bigint,
		  blks_read bigint,
		  blks_hit bigint,
		  tup_returned bigint,
		  tup_fetched bigint,
		  tup_inserted bigint,
		  tup_updated bigint,
		  tup_deleted bigint,
		  deadlocks bigint,
		  temp_files bigint,
		  temp_bytes bigint,
		  blk_read_time bigint,
		  blk_write_time bigint
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;	

	end$$;"""

query_check_single_db = """
	do $$ 
	begin
	
	IF not EXISTS (
	 SELECT 1
	 FROM   pg_class c
	 JOIN   pg_namespace n ON n.oid = c.relnamespace
	 WHERE  c.relname = 'psc_stat_activity_raw'
	 AND	n.nspname = 'public' AND c.relkind = 'r'
	 ) THEN

		CREATE UNLOGGED TABLE public.psc_stat_activity_raw
		(
		  dt timestamp with time zone DEFAULT now(),
		  datname character varying(255),
		  param character varying(255),
		  val numeric DEFAULT 0.0
		)
		WITH (
		  FILLFACTOR=50,
		  OIDS=FALSE
		);
	END IF;

	end$$;"""
	
query_single_db_t1 = """
	do $$
	begin
		delete from psc_stat_bgwriter_t1;
		INSERT INTO psc_stat_bgwriter_t1(
				now, checkpoints_timed, checkpoints_req, checkpoint_write_time, 
				checkpoint_sync_time, buffers_checkpoint, buffers_clean, maxwritten_clean, 
				buffers_backend, buffers_alloc, buffers_backend_fsync)
			select now(), checkpoints_timed, checkpoints_req, checkpoint_write_time, 
				checkpoint_sync_time, buffers_checkpoint, buffers_clean, maxwritten_clean, 
				buffers_backend, buffers_alloc, buffers_backend_fsync from pg_stat_bgwriter;
		delete from psc_stat_dbs_t1;
		INSERT INTO psc_stat_dbs_t1(
				now, datid, datname, numbackends, xact_commit, xact_rollback, 
				blks_read, blks_hit, tup_returned, tup_fetched, tup_inserted, 
				tup_updated, tup_deleted, deadlocks, temp_files, temp_bytes, blk_read_time, blk_write_time)
			select now(), datid, datname, numbackends, xact_commit, xact_rollback, blks_read, blks_hit, tup_returned, 
				tup_fetched, tup_inserted, tup_updated, tup_deleted, deadlocks, temp_files, temp_bytes, blk_read_time, blk_write_time from pg_stat_database;
	end$$;""";

query_single_db_t2 = """
	do $$ 
	begin
		delete from psc_stat_bgwriter_t2;
		INSERT INTO psc_stat_bgwriter_t2(
				now, checkpoints_timed, checkpoints_req, checkpoint_write_time, 
				checkpoint_sync_time, buffers_checkpoint, buffers_clean, maxwritten_clean, 
				buffers_backend, buffers_alloc, buffers_backend_fsync)
			select now(), checkpoints_timed, checkpoints_req, checkpoint_write_time, 
				checkpoint_sync_time, buffers_checkpoint, buffers_clean, maxwritten_clean, 
				buffers_backend, buffers_alloc, buffers_backend_fsync from pg_stat_bgwriter;
		delete from psc_stat_dbs_t2;
		INSERT INTO psc_stat_dbs_t2(
				now, datid, datname, numbackends, xact_commit, xact_rollback, 
				blks_read, blks_hit, tup_returned, tup_fetched, tup_inserted, 
				tup_updated, tup_deleted, deadlocks, temp_files, temp_bytes, blk_read_time, blk_write_time)
			select now(), datid, datname, numbackends, xact_commit, xact_rollback, blks_read, blks_hit, tup_returned, 
				tup_fetched, tup_inserted, tup_updated, tup_deleted, deadlocks, temp_files, temp_bytes, blk_read_time, blk_write_time from pg_stat_database;
	end$$;""";

query_single_db_sn = """
	do $$
	BEGIN
		INSERT INTO psc_stat_activity_raw( datname, param, val )
		select datname, state as state, count(state) from pg_stat_activity
		where pid <> pg_backend_pid()
		group by datname, state;

		if (SELECT current_setting('server_version_num'))::bigint >= 90600 then
			INSERT INTO psc_stat_activity_raw( datname, param, val )
			select T.datname, 'waiting_conns' as waiting_p, count(waiting) from (
				select datname, 
					(case when wait_event_type is not null 
					then 1 
					else 0 end) as waiting 
				from pg_stat_activity
				where wait_event_type is not null and pid <> pg_backend_pid()
			) T
			group by T.datname, waiting;
			
			INSERT INTO psc_stat_activity_raw( datname, param, val )
			select datname, 'longest_waiting' as longest_waiting, max( val ) from (
				select datname, 
				round( coalesce(extract(epoch from age(now(), xact_start)), 0)::numeric, 3 ) as val
				from pg_stat_activity 
				where wait_event_type is not null and pid <> pg_backend_pid()
				union all
				select datname, 0 
				from pg_database where datname not in ( 'template1', 'template0', 'postgres' )
			) T
			group by datname, longest_waiting;
		else
			INSERT INTO psc_stat_activity_raw( datname, param, val )
			select datname, 'waiting_conns' as waiting, count(waiting) from pg_stat_activity
			where waiting = true and pid <> pg_backend_pid()
			group by datname, waiting;
			
			INSERT INTO psc_stat_activity_raw( datname, param, val )
			select datname, 'longest_waiting' as longest_waiting, max( val ) from (
				select datname,
				round( coalesce(extract(epoch from age(now(), xact_start)), 0)::numeric, 3 ) as val
				from pg_stat_activity 
				where waiting = true and pid <> pg_backend_pid()
				union all
				select datname, 0 
				from pg_database where datname not in ( 'template1', 'template0', 'postgres' )
			) T
			group by datname, longest_waiting;
		end if;

		INSERT INTO psc_stat_activity_raw( datname, param, val )
		select datname, 'longest_active' as longest_active, max( val ) from (
			select datname, 
			round( coalesce(extract(epoch from age(now(), xact_start)), 0)::numeric, 3 ) as val
			from pg_stat_activity
			where state='active' and pid <> pg_backend_pid()
			union all
			select datname, 0
			from pg_database where datname not in ( 'template1', 'template0', 'postgres' )
		) T
		group by datname, longest_active;
		
		INSERT INTO psc_stat_activity_raw( datname, param, val )
		select datname, 'longest_idle_in_tx' as longest_idle_in_tx, max( val ) from (
			select datname,
			round( coalesce(extract(epoch from age(now(), xact_start)), 0)::numeric, 3 ) as val
			from pg_stat_activity
			where state='idle in transaction' and pid <> pg_backend_pid()
			union all
			select datname, 0
			from pg_database where datname not in ( 'template1', 'template0', 'postgres' )
		) T
		group by datname, longest_idle_in_tx;
		
		INSERT INTO psc_stat_activity_raw( datname, param, val )
		select d.datname, l.mode, count(l.mode) 
		from pg_locks l
		inner join pg_database d on l.database = d.oid
		group by d.datname, l.mode;

		INSERT INTO psc_stat_activity_raw( datname, param, val )
		select datname, autovacuum_workers, sum( cnt ) as cnt from
		(
				select datname, 'autovacuum_workers_total' as autovacuum_workers,
				sum(
					case when state = 'active' then 
						1 
					else
						0
					end
				) as cnt
				from pg_stat_activity
				where query ilike '%autovacuum:%' and query not ilike '%psc_stat_activity_raw%' 
					and pid <> pg_backend_pid()
				group by datname
				union all
				select datname, 'autovacuum_workers_wraparound' as autovacuum_workers,
				sum(
					case when state = 'active' then 
						1 
					else
						0
					end
				) as cnt
				from pg_stat_activity
				where query ilike '%autovacuum:%' and query ilike '%wraparound%' and query not ilike '%psc_stat_activity_raw%' 
					and pid <> pg_backend_pid()
				group by datname
				union all
				select datname, 'autovacuum_workers_total', 0 
				from pg_database where datname not in ( 'template1', 'template0', 'postgres' )
				union all
				select datname, 'autovacuum_workers_wraparound', 0 
				from pg_database where datname not in ( 'template1', 'template0', 'postgres' )		
		) T
		group by datname, autovacuum_workers;
		
		
	end$$;""";

#=======================================================================================================
def init_sys_stat( conn ):
	conn.execute( """set application_name = '""" + application_name + """'""" )
	conn.execute( """set timezone = '""" + time_zone + """';""" )
	query = conn.prepare( """select public.psc_get_node('""" + node_name + """', '""" + node_descr + """', '""" + node_host + """')""" )
	shm_name_res = query()
	conn.execute( """set search_path = 'n""" + str( shm_name_res[0][0] ) + """', 'public'""" )

def init_sys_stat_node( conn ):
	conn.execute( """set application_name = '""" + application_name + """'""" )
	conn.execute( """select public.psc_init_node('""" + node_name + """', '""" + node_descr + """', '""" + node_host + """')""" )

def get_pg_version( conn ):
	query = conn.prepare( """SHOW server_version""" )
	return LooseVersion( next( v[0] for v in query() ) )

def pg_sys_stat_snapshot():
	all_conns = []
	firs_node_db_conn = None
	sys_stat_db = None

	while True:	
		try:
			for db in dbs_list:
				all_conns.append( [ db[0], postgresql.open( db[1] ), db[1] ] )

			for conn in all_conns:
				conn[1].execute( """set application_name = '""" + application_name + """'""" )
				conn[1].execute( query_check_tables_all_dbs )

			for conn in all_conns:
				conn[1].execute( query_all_dbs_t1 )

			#====================================================================================================
			sys_stat_db = postgresql.open( sys_stat_conn_str )
			init_sys_stat( sys_stat_db ) 
			#====================================================================================================
			firs_node_db_conn = all_conns[0][1]
			firs_node_db_conn.execute( """set application_name = '""" + application_name + """'""" )
			
			firs_node_db_conn.execute( query_check_tables_single_db )
			firs_node_db_conn.execute( query_single_db_t1 )
			#====================================================================================================
			
			for conn in all_conns:			
				if not conn[1].closed:
					conn[1].close()
			del all_conns[:]
			if firs_node_db_conn is not None:
				if not firs_node_db_conn.closed:
					firs_node_db_conn.close()

			logger.log('pg_sys_stat_snapshot iteration finished! Sleep on ' + str( sleep_interval_pg_sys_stat ) + " seconds...", "Info" )	 
			time.sleep( sleep_interval_pg_sys_stat )

			for db in dbs_list:
				all_conns.append( [ db[0], postgresql.open( db[1] ), db[1] ] )

			for conn in all_conns:
				conn[1].execute( """set application_name = '""" + application_name + """'""" )
			
			for conn in all_conns:
				port = re.findall("""\:[0-9]+\/""", conn[2])[0]
				port = port.replace(":", "")
				port = port.replace("/", "")
				conn[1].execute( query_all_dbs_t2 )

				query = sys_stat_db.prepare( """select psc_get_db( '""" + str(conn[0]) + """')""" )
				db_id_res = query()
				db_id = db_id_res[0][0]

				#====================================================================================================
				query = conn[1].prepare( """
				select * from ( select 'by_idx_scan_per_sec'::text, relid, relname, dt,
				round( idx_scan_per_sec::numeric, 3) as idx_scan_per_sec 		
				from (
					select relid, relname, dt,
					idx_scan/seconds as idx_scan_per_sec
					from (
						SELECT
								( extract(epoch from (T2.now-T1.now)) ) as seconds,
								(T2.idx_scan - T1.idx_scan) as idx_scan, 
								T1.relname, T2.now as dt, T2.indexrelid as relid from psc_data_all_indexes_t1 T1
						inner join psc_data_all_indexes_t2 T2 on T1.indexrelid = T2.indexrelid
					) T where relname not in ( """ + exclude_tables + """ )
				) T where idx_scan_per_sec > 0
				order by idx_scan_per_sec desc nulls last
				limit """ + top_rels_in_snapshot + """ )T
				union
				select * from ( select 'by_idx_tup_read_per_sec'::text, relid, relname, dt,
				round( idx_tup_read_per_sec::numeric, 3) as idx_tup_read_per_sec 		
				from (
					select relid, relname, dt,
					idx_tup_read/seconds as idx_tup_read_per_sec
					from (
						SELECT
								( extract(epoch from (T2.now-T1.now)) ) as seconds,
								(T2.idx_tup_read - T1.idx_tup_read) as idx_tup_read, 
								T1.relname, T2.now as dt, T2.indexrelid as relid from psc_data_all_indexes_t1 T1
						inner join psc_data_all_indexes_t2 T2 on T1.indexrelid = T2.indexrelid
					) T where relname not in ( """ + exclude_tables + """ )
				) T where idx_tup_read_per_sec > 0
				order by idx_tup_read_per_sec desc nulls last
				limit """ + top_rels_in_snapshot + """ )T
				union				
				select * from ( select 'by_idx_tup_fetch_per_sec'::text, relid, relname, dt,
				round( idx_tup_fetch_per_sec::numeric, 3) as idx_tup_fetch_per_sec 		
				from (
					select relid, relname, dt,
					idx_tup_fetch/seconds as idx_tup_fetch_per_sec
					from (
						SELECT
								( extract(epoch from (T2.now-T1.now)) ) as seconds,
								(T2.idx_tup_fetch - T1.idx_tup_fetch) as idx_tup_fetch, 
								T1.relname, T2.now as dt, T2.indexrelid as relid from psc_data_all_indexes_t1 T1
						inner join psc_data_all_indexes_t2 T2 on T1.indexrelid = T2.indexrelid
					) T where relname not in ( """ + exclude_tables + """ )
				) T where idx_tup_fetch_per_sec > 0
				order by idx_tup_fetch_per_sec desc nulls last
				limit """ + top_rels_in_snapshot + """ )T
				union				
				select * from ( select 'fetched / scans'::text, relid, relname, dt,
				round( (idx_tup_fetch_per_sec::float/idx_scan_per_sec)::numeric, 3) as idx_scale3 		
				from (
					select relid, relname, dt,
					idx_scan/seconds as idx_scan_per_sec, 
					idx_tup_fetch/seconds as idx_tup_fetch_per_sec
					from (
						SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds,
								(T2.idx_scan - T1.idx_scan) as idx_scan, 
								(T2.idx_tup_fetch - T1.idx_tup_fetch) as idx_tup_fetch,
								T1.relname, T2.now as dt, T2.indexrelid as relid from psc_data_all_indexes_t1 T1
						inner join psc_data_all_indexes_t2 T2 on T1.indexrelid = T2.indexrelid
					) T where relname not in ( """ + exclude_tables + """ )
				) T where idx_scan_per_sec > 0 and idx_tup_fetch_per_sec > 0
				order by idx_scale3 desc nulls last 
				limit """ + top_rels_in_snapshot + """ )T
				union
				select * from ( select 'reads / scans'::text, relid, relname, dt, 
				round( (idx_tup_read_per_sec ::float/idx_scan_per_sec)::numeric, 3) as idx_scale2 		
				from (
					select relid, relname, dt, 
					idx_scan/seconds as idx_scan_per_sec, 
					idx_tup_read/seconds as idx_tup_read_per_sec
					from (
						SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds,
								(T2.idx_scan - T1.idx_scan) as idx_scan, 
								(T2.idx_tup_read - T1.idx_tup_read) as idx_tup_read,
								T1.relname, T2.now as dt, T2.indexrelid as relid from psc_data_all_indexes_t1 T1
						inner join psc_data_all_indexes_t2 T2 on T1.indexrelid = T2.indexrelid
					) T where relname not in ( """ + exclude_tables + """ )
				) T where idx_scan_per_sec > 0 and idx_tup_read_per_sec > 0 
				order by idx_scale2 desc nulls last 
				limit """ + top_rels_in_snapshot + """ )T
				union
				select * from ( select 'tup_fetch_sum'::text, relid, relname, dt, COALESCE(seq_tup_read_per_sec,0) + COALESCE(idx_tup_fetch_per_sec,0) as tup_fetch_sum from (
					select relid, relname, dt, 
					round(seq_tup_read/seconds::numeric, 3) as seq_tup_read_per_sec, 
					round(idx_tup_fetch/seconds::numeric, 3) as idx_tup_fetch_per_sec
					from (
						SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, 
								(T2.seq_tup_read - T1.seq_tup_read) as seq_tup_read, 
								(T2.idx_tup_fetch - T1.idx_tup_fetch) as idx_tup_fetch, 
								T1.relname, T2.now as dt, T2.relid from psc_data_t1 T1
						inner join psc_data_t2 T2 on T1.relid = T2.relid
					) T where relname not in ( """ + exclude_tables + """ )
				) T
				order by tup_fetch_sum desc nulls last
				limit """ + top_rels_in_snapshot + """ )T
				union
				select * from ( select 'idx_tup_fetch_per_sec'::text, relid, relname, dt, idx_tup_fetch_per_sec from (
					select relid, relname, dt, 
					round(idx_tup_fetch/seconds::numeric, 3) as idx_tup_fetch_per_sec
					from (
						SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, 
								(T2.idx_tup_fetch - T1.idx_tup_fetch) as idx_tup_fetch, 
								T1.relname, T2.now as dt, T2.relid from psc_data_t1 T1
						inner join psc_data_t2 T2 on T1.relid = T2.relid
					) T where relname not in ( """ + exclude_tables + """ )
				) T
				order by idx_tup_fetch_per_sec desc nulls last
				limit """ + top_rels_in_snapshot + """ )T
				union
				select * from ( select 'seq_tup_read_per_sec'::text, relid, relname, dt, seq_tup_read_per_sec from (
					select relid, relname, dt,  
					round(seq_tup_read/seconds::numeric, 3) as seq_tup_read_per_sec
					from (
						SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, 
								(T2.seq_tup_read - T1.seq_tup_read) as seq_tup_read,
								T1.relname, T2.now as dt, T2.relid from psc_data_t1 T1
						inner join psc_data_t2 T2 on T1.relid = T2.relid
					) T where relname not in ( """ + exclude_tables + """ )
				) T
				order by seq_tup_read_per_sec desc nulls last
				limit """ + top_rels_in_snapshot + """ )T
				union
				select * from ( select 'n_tup_ins_per_sec'::text, relid, relname, dt, n_tup_ins_per_sec from (
					select relid, relname, dt, 
					round(n_tup_ins/seconds::numeric, 3) as n_tup_ins_per_sec
					from (
						SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, 
								(T2.n_tup_ins - T1.n_tup_ins) as n_tup_ins, 
								T1.relname, T2.now as dt, T2.relid from psc_data_t1 T1
						inner join psc_data_t2 T2 on T1.relid = T2.relid
					) T where relname not in ( """ + exclude_tables + """ )
				) T
				order by n_tup_ins_per_sec desc nulls last
				limit """ + top_rels_in_snapshot + """ )T
				union
				select * from ( select 'n_tup_upd_per_sec'::text, relid, relname, dt, n_tup_upd_per_sec from (
					select relid, relname, dt,
					round(n_tup_upd/seconds::numeric, 3) as n_tup_upd_per_sec
					from (
						SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, 
								(T2.n_tup_upd - T1.n_tup_upd) as n_tup_upd,
								T1.relname, T2.now as dt, T2.relid from psc_data_t1 T1
						inner join psc_data_t2 T2 on T1.relid = T2.relid
					) T where relname not in ( """ + exclude_tables + """ )
				) T
				order by n_tup_upd_per_sec desc nulls last
				limit """ + top_rels_in_snapshot + """ )T
				union
				select * from ( select 'n_tup_del_per_sec'::text, relid, relname, dt, n_tup_del_per_sec from (
					select relid, relname, dt,
					round(n_tup_del/seconds::numeric, 3) as n_tup_del_per_sec
					from (
						SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, 
								(T2.n_tup_del - T1.n_tup_del) as n_tup_del,
								T1.relname, T2.now as dt, T2.relid from psc_data_t1 T1
						inner join psc_data_t2 T2 on T1.relid = T2.relid
					) T where relname not in ( """ + exclude_tables + """ )
				) T
				order by n_tup_del_per_sec desc nulls last
				limit """ + top_rels_in_snapshot + """ )T
				union
				select * from ( select 'n_tup_hot_upd_per_sec'::text, relid, relname, dt, n_tup_hot_upd_per_sec from (
					select relid, relname, dt,
					round(n_tup_hot_upd/seconds::numeric, 3) as n_tup_hot_upd_per_sec
					from (
						SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, 
								(T2.n_tup_hot_upd - T1.n_tup_hot_upd) as n_tup_hot_upd,
								T1.relname, T2.now as dt, T2.relid from psc_data_t1 T1
						inner join psc_data_t2 T2 on T1.relid = T2.relid
					) T where relname not in ( """ + exclude_tables + """ )
				) T
				order by n_tup_hot_upd_per_sec desc nulls last
				limit """ + top_rels_in_snapshot + """ )T
				union
				select * from ( select 'idx_blks_read_per_sec'::text, relid, relname, dt, idx_blks_read_per_sec from (
					select relid, relname, dt, 
					round(idx_blks_read/seconds::numeric, 3) as idx_blks_read_per_sec
					from (
						SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds,
								(T2.idx_blks_read - T1.idx_blks_read) as idx_blks_read,
								T1.relname, T2.now as dt, T2.relid from psc_data_io_t1 T1
						inner join psc_data_io_t2 T2 on T1.relid = T2.relid
					) T where relname not in ( """ + exclude_tables + """ )
				) T
				order by idx_blks_read_per_sec desc nulls last 
				limit """ + top_rels_in_snapshot + """ )T
				union
				select * from ( select 'heap_blks_read_per_sec'::text, relid, relname, dt, heap_blks_read_per_sec from (
					select relid, relname, dt, 
					round(heap_blks_read/seconds::numeric, 3) as heap_blks_read_per_sec
					from (
						SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds,
								(T2.heap_blks_read - T1.heap_blks_read) as heap_blks_read, 
								T1.relname, T2.now as dt, T2.relid from psc_data_io_t1 T1
						inner join psc_data_io_t2 T2 on T1.relid = T2.relid
					) T where relname not in ( """ + exclude_tables + """ )
				) T
				order by heap_blks_read_per_sec desc nulls last
				limit """ + top_rels_in_snapshot + """ )T
				union
				select * from ( select 'reads / fetched'::text, relid, relname, dt, 
				round( (idx_tup_read_per_sec::float/idx_tup_fetch_per_sec)::numeric, 3) as idx_scale1 	
				from (
					select relid, relname, dt, 
					idx_tup_read/seconds as idx_tup_read_per_sec,
					idx_tup_fetch/seconds as idx_tup_fetch_per_sec
					from (
						SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds,
								(T2.idx_tup_read - T1.idx_tup_read) as idx_tup_read,
								(T2.idx_tup_fetch - T1.idx_tup_fetch) as idx_tup_fetch,
								T1.relname, T2.now as dt, T2.indexrelid as relid from psc_data_all_indexes_t1 T1
						inner join psc_data_all_indexes_t2 T2 on T1.indexrelid = T2.indexrelid
					) T where relname not in ( """ + exclude_tables + """ )
				) T where idx_tup_read_per_sec > 0 and idx_tup_fetch_per_sec > 0 
				order by idx_scale1 desc nulls last 
				limit """ + top_rels_in_snapshot + """ )T""" )
				res_data = query()
				
				stm = sys_stat_db.prepare( """
				INSERT INTO psc_tbls_stat(
					dt, db_id, param_id, tbl_id, val)
				values( $5, $1, ( select psc_get_param( $2 ) ), ( select psc_get_tbl( $3, $4, $1 ) ), $6 )""" )
				#psc_get_tbl( relid, relname, db_id )
				with sys_stat_db.xact():			
					for rec in res_data:
						stm.first( 	db_id, 			str( rec[0] ), 		rec[1], 		rec[2], 			rec[3], 						rec[4] )
									#['BIGINT', 	'pg_catalog.text', 	'BIGINT', 		'pg_catalog.text', 	'TIMESTAMP WITH TIME ZONE', 	'NUMERIC']
									# db_id			param				relid	  		relname				dt								val
									# $1			$2					$3	  			$4					$5								$6
				#====================================================================================================
				#pg_stat_statements processing
				query = conn[1].prepare( """
				select T.dt, T.query, T.queryid, abs(T.calls_res) as val, 'stm_calls'::text as metric
				from (
					select
					t1.query,
					t2.calls - t1.calls as calls_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where t2.calls - t1.calls <> 0  
					order by calls_res desc
					limit """ + top_stm_queries_in_snapshot + """ 
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.total_time_res) as val, 'stm_total_time'::text as metric
				from (
					select t1.query,
					t2.total_time - t1.total_time as total_time_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where round((t2.total_time - t1.total_time)::numeric, 3) <> 0
					order by total_time_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.rows_res) as val, 'stm_rows'::text as metric
				from (
					select t1.query,
					t2.rows - t1.rows as rows_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where t2.rows - t1.rows <> 0
					order by rows_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.shared_blks_hit_res) as val, 'stm_shared_blks_hit'::text as metric
				from (
					select t1.query,
					t2.shared_blks_hit - t1.shared_blks_hit as shared_blks_hit_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where t2.shared_blks_hit - t1.shared_blks_hit <> 0
					order by shared_blks_hit_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.shared_blks_read_res) as val, 'stm_shared_blks_read'::text as metric
				from (
					select t1.query,
					t2.shared_blks_read - t1.shared_blks_read as shared_blks_read_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where t2.shared_blks_read - t1.shared_blks_read <> 0
					order by shared_blks_read_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.shared_blks_dirtied_res) as val, 'stm_shared_blks_dirtied'::text as metric
				from (
					select t1.query,
					t2.shared_blks_dirtied - t1.shared_blks_dirtied as shared_blks_dirtied_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where t2.shared_blks_dirtied - t1.shared_blks_dirtied <> 0
					order by shared_blks_dirtied_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.shared_blks_written_res) as val, 'stm_shared_blks_written'::text as metric
				from (
					select t1.query,
					t2.shared_blks_written - t1.shared_blks_written as shared_blks_written_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where t2.shared_blks_written - t1.shared_blks_written <> 0
					order by shared_blks_written_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.local_blks_hit_res) as val, 'stm_local_blks_hit'::text as metric
				from (
					select t1.query,
					t2.local_blks_hit - t1.local_blks_hit as local_blks_hit_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where t2.local_blks_hit - t1.local_blks_hit <> 0
					order by local_blks_hit_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.local_blks_read_res) as val, 'stm_local_blks_read'::text as metric
				from (
					select t1.query,
					t2.local_blks_read - t1.local_blks_read as local_blks_read_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where t2.local_blks_read - t1.local_blks_read <> 0
					order by local_blks_read_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.local_blks_dirtied_res) as val, 'stm_local_blks_dirtied'::text as metric
				from (
					select t1.query,
					t2.local_blks_dirtied - t1.local_blks_dirtied as local_blks_dirtied_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where t2.local_blks_dirtied - t1.local_blks_dirtied <> 0
					order by local_blks_dirtied_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.local_blks_written_res) as val, 'stm_local_blks_written'::text as metric
				from (
					select t1.query,
					t2.local_blks_written - t1.local_blks_written as local_blks_written_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where t2.local_blks_written - t1.local_blks_written <> 0
					order by local_blks_written_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.temp_blks_read_res) as val, 'stm_temp_blks_read'::text as metric
				from (
					select t1.query,
					t2.temp_blks_read - t1.temp_blks_read as temp_blks_read_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where t2.temp_blks_read - t1.temp_blks_read <> 0
					order by temp_blks_read_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.temp_blks_written_res) as val, 'stm_temp_blks_written'::text as metric
				from (
					select t1.query,
					t2.temp_blks_written - t1.temp_blks_written as temp_blks_written_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where t2.temp_blks_written - t1.temp_blks_written <> 0
					order by temp_blks_written_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.blk_read_time_res) as val, 'stm_blk_read_time'::text as metric
				from (
					select t1.query,
					t2.blk_read_time - t1.blk_read_time as blk_read_time_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where round((t2.blk_read_time - t1.blk_read_time)::numeric, 3) <> 0
					order by blk_read_time_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				union
				select T.dt, T.query, T.queryid, abs(T.blk_write_time_res) as val, 'stm_blk_write_time'::text as metric
				from (
					select t1.query,
					t2.blk_write_time - t1.blk_write_time as blk_write_time_res,
					t2.now as dt,
					(select ('x'||substr(md5(t1.queryid::text || t1.userid::text),1,16))::bit(64)::bigint) as queryid
					from psc_stm_t1 t1
					inner join psc_stm_t2 t2 on t2.queryid = t1.queryid and t2.userid = t1.userid
					where round((t2.blk_write_time - t1.blk_write_time)::numeric, 3) <> 0
					order by blk_write_time_res desc
					limit """ + top_stm_queries_in_snapshot + """
				) T
				""" )
				res_data = query()
				
				stm = sys_stat_db.prepare( """
				INSERT INTO psc_stm_stat(
					dt, db_id, param_id, query_id, val)
				values( $2, $1, ( select psc_get_param( $6 ) ), ( select psc_get_stm_query( $1, $4, $3 ) ), $5 )""" )
				#psc_get_stm_query( db_id, query_id, query )
				with sys_stat_db.xact():
					for rec in res_data:
						stm.first( db_id, rec[0], rec[1], rec[2], rec[3], rec[4] )
						#			$1		$2		$3		$4		$5		$6
						#					dt		query	queryid val		metric
				#====================================================================================================
				
				conn[1].execute( query_all_dbs_t1 )
			
			
			firs_node_db_conn = all_conns[0][1]
			firs_node_db_conn.execute( """set application_name = '""" + application_name + """'""" )
			firs_node_db_conn.execute( query_single_db_t2 )
			
			#====================================================================================================
			query = firs_node_db_conn.prepare( """
				select 'checkpoints_timed', (select checkpoints_timed from psc_stat_bgwriter_t2 limit 1) -
				(select checkpoints_timed from psc_stat_bgwriter_t1 limit 1)
				union
				select 'checkpoints_req' , (select checkpoints_req from psc_stat_bgwriter_t2 limit 1) -
				(select checkpoints_req from psc_stat_bgwriter_t1 limit 1)
				union
				select 'checkpoint_write_time' , (select checkpoint_write_time from psc_stat_bgwriter_t2 limit 1) -
				(select checkpoint_write_time from psc_stat_bgwriter_t1 limit 1)
				union
				select 'checkpoint_sync_time' , (select checkpoint_sync_time from psc_stat_bgwriter_t2 limit 1) -
				(select checkpoint_sync_time from psc_stat_bgwriter_t1 limit 1)
				union
				select 'buffers_checkpoint' , (select buffers_checkpoint from psc_stat_bgwriter_t2 limit 1) -
				(select buffers_checkpoint from psc_stat_bgwriter_t1 limit 1)
				union
				select 'buffers_clean' , (select buffers_clean from psc_stat_bgwriter_t2 limit 1) -
				(select buffers_clean from psc_stat_bgwriter_t1 limit 1)
				union
				select 'maxwritten_clean' , (select maxwritten_clean from psc_stat_bgwriter_t2 limit 1) -
				(select maxwritten_clean from psc_stat_bgwriter_t1 limit 1)
				union
				select 'buffers_backend' , (select buffers_backend from psc_stat_bgwriter_t2 limit 1) -
				(select buffers_backend from psc_stat_bgwriter_t1 limit 1)
				union
				select 'buffers_alloc' , (select buffers_alloc from psc_stat_bgwriter_t2 limit 1) -
				(select buffers_alloc from psc_stat_bgwriter_t1 limit 1)
				union
				select 'buffers_backend_fsync' , (select buffers_backend_fsync from psc_stat_bgwriter_t2 limit 1) -
				(select buffers_backend_fsync from psc_stat_bgwriter_t1 limit 1)""" )
			res_data = query()
			
			stm = sys_stat_db.prepare( """
			INSERT INTO psc_common_stat( param_id, val) values( ( select psc_get_param( $1 ) ), $2 )""" )
			with sys_stat_db.xact():			
				for rec in res_data:
					stm.first( rec[0], rec[1] )
			#====================================================================================================

			#====================================================================================================
			#simple values
			query = firs_node_db_conn.prepare( """
				select 'xlog_segments', count(1) from pg_ls_dir('""" + \
					( 'pg_wal' if get_pg_version(firs_node_db_conn) >= LooseVersion("10") else 'pg_xlog' ) + """') limit 1
				""" )
			res_data = query()
			
			stm = sys_stat_db.prepare( """
			INSERT INTO psc_common_stat( param_id, val) values( ( select psc_get_param( $1 ) ), $2 )""" )
			with sys_stat_db.xact():			
				for rec in res_data:
					stm.first( rec[0], rec[1] )
			#====================================================================================================
			
			#====================================================================================================
			query = firs_node_db_conn.prepare( """select T.datname::text,'numbackends', round(numbackends/2::numeric, 3) 
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.numbackends + T1.numbackends) as numbackends
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T
			union
			select T.datname::text,'xact_commit_per_sec', round(xact_commit/seconds::numeric, 3) 
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.xact_commit - T1.xact_commit) as xact_commit
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T
			union
			select T.datname::text,'xact_rollback_per_sec', round(xact_rollback/seconds::numeric, 3) 
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.xact_rollback - T1.xact_rollback) as xact_rollback
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T
			union
			select T.datname::text,'blks_read_per_sec', round(blks_read/seconds::numeric, 3)
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.blks_read - T1.blks_read) as blks_read
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T	
			union
			select T.datname::text,'blks_hit_per_sec', round(blks_hit/seconds::numeric, 3) 
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.blks_hit - T1.blks_hit) as blks_hit
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T	
			union
			select T.datname::text,'tup_returned_per_sec', round(tup_returned/seconds::numeric, 3) 
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.tup_returned - T1.tup_returned) as tup_returned
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T	
			union
			select T.datname::text,'tup_fetched_per_sec', round(tup_fetched/seconds::numeric, 3) 
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.tup_fetched - T1.tup_fetched) as tup_fetched
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T	
			union
			select T.datname::text,'tup_inserted_per_sec', round(tup_inserted/seconds::numeric, 3)
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.tup_inserted - T1.tup_inserted) as tup_inserted
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T		
			union
			select T.datname::text,'tup_updated_per_sec', round(tup_updated/seconds::numeric, 3) 
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.tup_updated - T1.tup_updated) as tup_updated
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T	
			union
			select T.datname::text,'tup_deleted_per_sec', round(tup_deleted/seconds::numeric, 3) 
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.tup_deleted - T1.tup_deleted) as tup_deleted
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T	
			union
			select T.datname::text,'deadlocks', deadlocks
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.deadlocks - T1.deadlocks) as deadlocks
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T	
			union
			select T.datname::text,'temp_files', temp_files
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.temp_files - T1.temp_files) as temp_files
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T
			union
			select T.datname::text,'temp_bytes', temp_bytes
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.temp_bytes - T1.temp_bytes) as temp_bytes
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T
			union
			select T.datname::text,'blk_read_time', blk_read_time
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.blk_read_time - T1.blk_read_time) as blk_read_time
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T
			union
			select T.datname::text,'blk_write_time', blk_write_time
			from (
				SELECT ( extract(epoch from (T2.now-T1.now)) ) as seconds, T1.datid, T1.datname, 
				(T2.blk_write_time - T1.blk_write_time) as blk_write_time
				from psc_stat_dbs_t1 T1
				inner join psc_stat_dbs_t2 T2 on T1.datid = T2.datid
			) T""" )
			
			res_data = query()
			
			stm = sys_stat_db.prepare( """
				INSERT INTO psc_dbs_stat( db_id, param_id, val)
					values( ( select psc_get_db($1) ), ( select psc_get_param($2) ), $3 )""" )
			with sys_stat_db.xact():			
				for rec in res_data:
					stm.first( rec[0], rec[1], rec[2] )
			#====================================================================================================			

			firs_node_db_conn.execute( query_single_db_t1 )

		except Exception as e:
			logger.log( "Connection pg_sys_stat_snapshot error: " + str( e ), "Error" )
			time.sleep(sleep_interval_on_exception)
		finally:
			for conn in all_conns:			
				if not conn[1].closed:
					conn[1].close()
			del all_conns[:]
			if firs_node_db_conn is not None:
				if not firs_node_db_conn.closed:
					firs_node_db_conn.close()
			if sys_stat_db is not None:
				sys_stat_db.close()
				
#=======================================================================================================

def pg_conn_snapshot():
	sys_stat_db = None
	firs_node_db_conn = None
	while True:
		try:
			sys_stat_db = postgresql.open( sys_stat_conn_str )
			init_sys_stat( sys_stat_db )			

			firs_node_db = dbs_list[0]
			firs_node_db_conn = postgresql.open( firs_node_db[1] )
			firs_node_db_conn.execute( """set application_name = '""" + application_name + """'""" )

			sn_id = 0
			query = sys_stat_db.prepare( """INSERT INTO psc_snapshots(dt) VALUES (now()) returning id""" )
			sn_id_res = query()
			sn_id = sn_id_res[0][0]
			
			#====================================================================================================
			if get_pg_version(firs_node_db_conn) >= LooseVersion("9.6"):
				query = firs_node_db_conn.prepare( """
					select datname::text, usename::text, application_name, state::text, pid::bigint, client_addr, 
					client_port, backend_start, xact_start, query_start, state_change, wait_event_type, wait_event, query 
					from pg_stat_activity""" )
				res_data = query()
				
				stm = sys_stat_db.prepare( """
				INSERT INTO psc_conns( sn_id, db_id, user_id, app_name, conn_state, pid, client_addr, 
						client_port, backend_start, xact_start, query_start, state_change, 
						wait_event_type, wait_event, query)
					VALUES( $1, (select psc_get_db($2)),(select psc_get_db_user($3)),(select psc_get_app_name($4)),
						(select psc_get_conn_state($5)), $6, $7, $8, $9, $10, $11, $12, (select psc_get_wait_type($13)), (select psc_get_wait_name($14)), $15 )""" )	
				with sys_stat_db.xact():			
					for rec in res_data:
						stm.first( sn_id, str( rec[0] ), str( rec[1] ), str( rec[2] ), str( rec[3] ), rec[4], '127.0.0.1' if rec[5] is None else rec[5], 
							rec[6], rec[7], rec[8], rec[9], rec[10], rec[11], rec[12], rec[13] )
			else:
				query = firs_node_db_conn.prepare( """
					select datname::text, usename::text, application_name::text, state::text, pid::bigint, client_addr, 
					client_port, backend_start, xact_start, query_start, state_change, waiting, query 
					from pg_stat_activity""" )
				res_data = query()
				
				stm = sys_stat_db.prepare( """
				INSERT INTO psc_conns( sn_id, db_id, user_id, app_name, conn_state, pid, client_addr, 
						client_port, backend_start, xact_start, query_start, state_change, 
						waiting, query)
					VALUES( $1, (select psc_get_db($2)),(select psc_get_db_user($3)),(select psc_get_app_name($4)),
						(select psc_get_conn_state($5)), $6, $7, $8, $9, $10, $11, $12, $13, $14 )""" )
				with sys_stat_db.xact():			
					for rec in res_data:
						stm.first( sn_id, str( rec[0] ), str( rec[1] ), str( rec[2] ), str( rec[3] ), rec[4], '127.0.0.1' if rec[5] is None else rec[5], 
							rec[6], rec[7], rec[8], rec[9], rec[10], rec[11], rec[12] )
			#====================================================================================================

			query = firs_node_db_conn.prepare( """
				select T.waiting_locktype, T.waiting_mode, T.waiting_database_name, T.waiting_database_id, T.waiting_table, T.waiting_query, 
					T.waiting_pid, T.waiting_tx, T.other_locktype, T.other_mode, T.other_table, T.other_query, T.other_pid, T.other_tx, 
					T.waiting_table::regclass, T.other_table::regclass
				from
				  (
					SELECT waiting.locktype AS waiting_locktype,
						waiting.relation AS waiting_table,
						db.datname AS waiting_database_name,
						waiting.database AS waiting_database_id,
						waiting_stm.query AS waiting_query,
						waiting.mode AS waiting_mode,
						waiting.pid AS waiting_pid,
						waiting.transactionid as waiting_tx,
						other.locktype AS other_locktype,
						other.relation AS other_table,
						other_stm.query AS other_query,
						other.mode AS other_mode,
						other.pid AS other_pid,
						other.transactionid as other_tx
					   FROM pg_locks waiting
						 JOIN pg_stat_activity waiting_stm ON waiting_stm.pid = waiting.pid
						 JOIN pg_locks other ON waiting.database = other.database AND waiting.relation = other.relation OR waiting.transactionid = other.transactionid
						 JOIN pg_stat_activity other_stm ON other_stm.pid = other.pid
						 JOIN pg_database db ON db.oid = waiting.database
					  WHERE NOT waiting.granted AND waiting.pid <> other.pid
				  ) T limit """ + locks_limit_in_snapshot + """;""" )

			res_data = query()
			
			stm = sys_stat_db.prepare( """
				INSERT INTO psc_locks(
					sn_id, waiting_locktype_id, waiting_mode_id, waiting_db_id, waiting_table_id, 
					waiting_query, waiting_pid, waiting_xid, other_locktype_id, other_mode_id, 
					other_table_id, other_query, other_pid, other_xid )
					VALUES( $1, (select psc_get_lock_type($2)), (select psc_get_lock_mode($3)), (select psc_get_db($4)), ( select psc_get_tbl( $6::bigint, $16, $5 ) ), $7, $8, $9,
					  (select psc_get_lock_type($10)), (select psc_get_lock_mode($11)), ( select psc_get_tbl( $12::bigint, $17, $5) ), $13, $14, $15 )""" )
			with sys_stat_db.xact():
				for rec in res_data:
					stm.first( sn_id, str( rec[0] ), str( rec[1] ), rec[2], rec[3], rec[4], str(rec[5]), rec[6], 
							rec[7], str( rec[8] ), str(rec[9]), rec[10], str(rec[11]), rec[12], rec[13], rec[14], rec[15] )

		except Exception as e:
			logger.log( "Connection pg_conn_snapshot error: " + str( e ), "Error" )
			time.sleep(sleep_interval_on_exception)			
		finally:
			if sys_stat_db is not None:
				if not sys_stat_db.closed:
					sys_stat_db.close()
			if firs_node_db_conn is not None:	
				if not firs_node_db_conn.closed:
					firs_node_db_conn.close()

			logger.log('pg_conn_snapshot iteration finished! Sleep on ' + str( sleep_interval_pg_conn_snapshot ) + " seconds...", "Info" )
			time.sleep( int( sleep_interval_pg_conn_snapshot ) )

#=======================================================================================================
def pg_single_db_sn():
	sys_stat_db = None
	firs_node_db_conn = None
	while True:
		try:
			firs_node_db = dbs_list[0]
			firs_node_db_conn = postgresql.open( firs_node_db[1] )
			firs_node_db_conn.execute( """set application_name = '""" + application_name + """'""" )
			firs_node_db_conn.execute( query_check_single_db )

			#====================================================================================================
			firs_node_db_conn.execute( """delete from psc_stat_activity_raw;""" )
			
			for step in range(0, pg_single_db_sn_steps ):
				firs_node_db_conn.execute( query_single_db_sn )
				time.sleep(sleep_interval_pg_single_db_sn)
			
			query = firs_node_db_conn.prepare( """
				select datname, param, 
					case when param in ('longest_active', 'longest_idle_in_tx', 'longest_waiting') then
						round(max( val ), 3)
					else
						round(avg( val ), 3)
					end
				from psc_stat_activity_raw
				group by datname, param;""" )
			res_data = query()
			
			sys_stat_db = postgresql.open( sys_stat_conn_str )
			init_sys_stat( sys_stat_db )	
			
			stm = sys_stat_db.prepare( """
				INSERT INTO psc_dbs_stat( db_id, param_id, val)
				values( ( select psc_get_db( $1 ) ), ( select psc_get_param( $2 ) ),$3 )""" )
			with sys_stat_db.xact():			
				for rec in res_data:
					stm.first( rec[0], str( rec[1] ), rec[2] )
			#====================================================================================================

		except Exception as e:
			logger.log( "Connection pg_single_db_sn error: " + str( e ), "Error" )
			time.sleep(sleep_interval_on_exception)			
		finally:
			if sys_stat_db is not None:
				if not sys_stat_db.closed:
					sys_stat_db.close()
			if firs_node_db_conn is not None:	
				if not firs_node_db_conn.closed:
					firs_node_db_conn.close()

			logger.log('pg_single_db_sn iteration finished! Start next iteration...', "Info" )

#=======================================================================================================
def make_iostat_data():
	def avg_param( param_name, data ):
		result = 0
		cnt = 0
		for v in data:
			if v[0] == param_name:
				result += float( v[1] )
				cnt += 1
		if cnt != 0:
			return [ param_name, result/cnt ]
		return [ param_name, 0 ]
		
	def avg_param_by_device( device, param_name, data ):
		result = 0
		cnt = 0
		for v in data:
			if v[0] == device and v[1] == param_name:
				result += float( v[2] )
				cnt += 1
		if cnt != 0:
			return [ device, param_name, result/cnt ]
		return [ device, param_name, 0 ]	

	def diff_param_by_device( device, param_name, data ):
		v1 = 0
		v2 = 0
		cnt = 0	
		for v in data:
			if cnt == 0 and v[0] == device and v[1] == param_name:
				v1 = int( v[2] )
				cnt += 1
			else:
				if cnt == 1 and v[0] == device and v[1] == param_name:
					v2 = int( v[2] )
					cnt += 1
		if cnt != 0:
			return [ device, param_name, abs( v1 - v2 ) ]
		return [ device, param_name, 0 ]	

	def diff_param_per_sec_by_device( device, param_name, data, seconds ):
		v1 = 0
		v2 = 0
		cnt = 0	
		for v in data:
			if cnt == 0 and v[0] == device and v[1] == param_name:
				v1 = int( v[2] )
				cnt += 1
			else:
				if cnt == 1 and v[0] == device and v[1] == param_name:
					v2 = int( v[2] )
					cnt += 1
		if cnt != 0:
			return [ device, param_name, abs( v1 - v2 ) / seconds ]
		return [ device, param_name, 0 ]
		
	def get_devices( data ):
		result = []
		for v in data:
			if v[0] not in result:
				result.append( v[0] )
		return result
		
	network_vals = []
	cpu_vals = []
	io_vals = []
	count_cpu = 0
	count_io = 0
	
	def write_network_vals( cmd_netstat ):
		count_devices = 0
		for line in cmd_netstat.stdout:
			columns = line.decode('utf8').split()
			#cmd_netstat	
			#['Kernel', 'Interface', 'table']
			#['Iface', 'MTU', 'Met', 'RX-OK', 'RX-ERR', 'RX-DRP', 'RX-OVR', 'TX-OK', 'TX-ERR', 'TX-DRP', 'TX-OVR', 'Flg']
			#['br0', '1500', '0', '4141303911', '0', '0', '0', '2202772722', '0', '0', '0', 'BMRU']
			#['eth0', '1500', '0', '4734369032', '712098', '0', '6142', '2675888623', '0', '0', '0', 'BMRU']
			#['eth1', '1500', '0', '55742929321', '0', '0', '1175', '42341968586', '0', '0', '0', 'BMRU']
			#['lo', '16436', '0', '103472698362', '0', '0', '0', '103472698362', '0', '0', '0', 'LRU']
			#['virbr0', '1500', '0', '0', '0', '0', '0', '0', '0', '0', '0', 'BMRU']
			#['vnet0', '1500', '0', '97346763', '0', '0', '0', '919087924', '0', '0', '1272', 'BMRU']
			#['vnet1', '1500', '0', '0', '0', '0', '0', '267503781', '0', '0', '4164', 'BMRU']	

			if len( columns ) > 0:
				if columns[0] == 'Iface':
					count_devices += 1

				if len( columns ) == 12 and columns[0] != 'Iface' and count_devices >= 1:
					network_vals.append( [ columns[0], 'RX-OK',  columns[3] ] )
					network_vals.append( [ columns[0], 'RX-ERR', columns[4] ] )
					network_vals.append( [ columns[0], 'RX-DRP', columns[5] ] )
					network_vals.append( [ columns[0], 'RX-OVR', columns[6] ] )
					network_vals.append( [ columns[0], 'TX-OK',  columns[7] ] )
					network_vals.append( [ columns[0], 'TX-ERR', columns[8] ] )
					network_vals.append( [ columns[0], 'TX-DRP', columns[9] ] )
					network_vals.append( [ columns[0], 'TX-OVR', columns[10] ] )

				if len( columns ) == 11 and columns[0] != 'Iface' and count_devices >= 1:
					network_vals.append( [ columns[0], 'RX-OK',  columns[2] ] )
					network_vals.append( [ columns[0], 'RX-ERR', columns[3] ] )
					network_vals.append( [ columns[0], 'RX-DRP', columns[4] ] )
					network_vals.append( [ columns[0], 'RX-OVR', columns[5] ] )
					network_vals.append( [ columns[0], 'TX-OK',  columns[6] ] )
					network_vals.append( [ columns[0], 'TX-ERR', columns[7] ] )
					network_vals.append( [ columns[0], 'TX-DRP', columns[8] ] )
					network_vals.append( [ columns[0], 'TX-OVR', columns[9] ] )

		network_devices = get_devices( network_vals )
		for device in network_devices:
			if os.path.exists('/sys/class/net/' + device + '/statistics'):
				rx_bytes = os.popen('cat /sys/class/net/' + device + '/statistics/rx_bytes').read()
				tx_bytes = os.popen('cat /sys/class/net/' + device + '/statistics/tx_bytes').read()
				network_vals.append( [ device, 'rx_bytes', int(rx_bytes) ] )
				network_vals.append( [ device, 'tx_bytes', int(tx_bytes) ] )

	cmd_netstat_t1 = subprocess.Popen('netstat -i',shell=True,stdout=subprocess.PIPE)
	write_network_vals( cmd_netstat_t1 )

	cmd_iostat = subprocess.Popen('iostat -d -c -m -x ' + sleep_interval_os_stat,shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = cmd_iostat.communicate()
	if str( err ).find('Cannot find disk data') > -1 or str( err ).find('iostat: command not found') > -1:
		time.sleep( sleep_interval_os_stat_if_iostat_not_working )
	else:
		lines = out.decode('utf8').split('\n')
		for line in lines:
			columns = line.split()
			#cmd_iostat	
			#[]
			#['avg-cpu:', '%user', '%nice', '%system', '%iowait', '%steal', '%idle']
			#['9.20', '0.00', '0.95', '0.34', '0.00', '89.51']
			#[]
			#['Device:', 'rrqm/s', 'wrqm/s', 'r/s', 'w/s', 'rMB/s', 'wMB/s', 'avgrq-sz', 'avgqu-sz', 'await', 'r_await', 'w_await', 'svctm', '%util']
			#['sda', '0.00', '5.70', '1.06', '5.64', '0.05', '0.21', '81.05', '0.14', '21.44', '4.10', '24.70', '0.30', '0.20']
			#['sdb', '0.01', '50.58', '159.75', '602.12', '8.65', '7.04', '42.18', '0.32', '0.42', '1.27', '0.19', '0.07', '5.68']
			#[]
		
			if len( columns ) > 0:
				if columns[0] == 'avg-cpu:':
					count_cpu += 1
				if columns[0] == 'Device:' or  columns[0] == 'Device':
					count_io += 1	

				if len( columns ) == 6 and columns[0] != 'avg-cpu:' and count_cpu >= 2:
					cpu_vals.append( [ '%user', columns[0] ] )
					cpu_vals.append( [ '%nice', columns[1] ] )
					cpu_vals.append( [ '%system', columns[2] ] )
					if float( columns[3] ) <= 100:
						cpu_vals.append( [ '%iowait', columns[3] ] )
					cpu_vals.append( [ '%steal', columns[4] ] )
					cpu_vals.append( [ '%idle', columns[5] ] )

				#if not exists 'r_await', 'w_await' columns and not first measurement
				if len( columns ) == 12 and columns[0] != 'Device:' and count_io >= 2:
					io_vals.append( [ columns[0], 'rrqm/s', columns[1] ] )
					io_vals.append( [ columns[0], 'wrqm/s', columns[2] ] )
					io_vals.append( [ columns[0], 'r/s', columns[3] ] )
					io_vals.append( [ columns[0], 'w/s', columns[4] ] )
					io_vals.append( [ columns[0], 'rMB/s', columns[5] ] )
					io_vals.append( [ columns[0], 'wMB/s', columns[6] ] )
					io_vals.append( [ columns[0], 'avgrq-sz', columns[7] ] )
					io_vals.append( [ columns[0], 'avgqu-sz', columns[8] ] )
					io_vals.append( [ columns[0], 'await', columns[9] ] )
					io_vals.append( [ columns[0], 'svctm', columns[10] ] )
					io_vals.append( [ columns[0], '%util', columns[11] ] )

				#if exists 'r_await', 'w_await' columns and not first measurement
				if len( columns ) == 14 and columns[0] != 'Device:' and count_io >= 2:
					io_vals.append( [ columns[0], 'rrqm/s', columns[1] ] )
					io_vals.append( [ columns[0], 'wrqm/s', columns[2] ] )
					io_vals.append( [ columns[0], 'r/s', columns[3] ] )
					io_vals.append( [ columns[0], 'w/s', columns[4] ] )
					io_vals.append( [ columns[0], 'rMB/s', columns[5] ] )
					io_vals.append( [ columns[0], 'wMB/s', columns[6] ] )
					io_vals.append( [ columns[0], 'avgrq-sz', columns[7] ] )
					io_vals.append( [ columns[0], 'avgqu-sz', columns[8] ] )
					io_vals.append( [ columns[0], 'await', columns[9] ] )
					io_vals.append( [ columns[0], 'svctm', columns[12] ] )
					io_vals.append( [ columns[0], '%util', columns[13] ] )

				#if exists 'r_await', 'w_await' columns and not first measurement
				if len( columns ) == 16 and columns[0] != 'Device' and count_io >= 2:
					#sysstat version 11.5.7
					#Device            r/s     w/s     rMB/s     wMB/s   rrqm/s   wrqm/s  %rrqm  %wrqm r_await w_await aqu-sz rareq-sz wareq-sz  svctm  %util
					#sda              0.00    4.21      0.00      0.02     0.00     1.20   0.00  22.22    0.00    0.19   0.00     0.00     5.14   0.19   0.08
					#					1		2		3			4		5		6		7		8		9		10		11		12		13		14		15
					#r/s - The number (after merges) of read requests completed per second for the device. 
					#w/s - The number (after merges) of write requests completed per second for the device. 
					#sec/s (kB/s, MB/s) - The number of sectors (kilobytes, megabytes) read from or written to the device per second.
					#rsec/s (rkB/s, rMB/s) - The number of sectors (kilobytes, megabytes) read from the device per second. 
					#wsec/s (wkB/s, wMB/s) - The number of sectors (kilobytes, megabytes) written to the device per second.
					#rqm/s - The number of I/O requests merged per second that were queued to the device.
					#rrqm/s - The number of read requests merged per second that were queued to the device. 
					#wrqm/s - The number of write requests merged per second that were queued to the device.
					#%rrqm - The percentage of read requests merged together before being sent to the device.
					#%wrqm - The percentage of write requests merged together before being sent to the device.
					#areq-sz - The average size (in kilobytes) of the requests that were issued to the device.
					#	Note: In previous versions, this field was known as avgrq-sz and was expressed in sectors.
					#rareq-sz - The average size (in kilobytes) of the read requests that were issued to the device.
					#wareq-sz - The average size (in kilobytes) of the write requests that were issued to the device.
					
					#await - The average time (in milliseconds) for I/O requests issued to the device to be served. This includes the time spent by the requests in queue and the time spent servicing them.
					#r_await - The average time (in milliseconds) for read requests issued to the device to be served. This includes the time spent by the requests in queue and the time spent servicing them.
					#w_await - The average time (in milliseconds) for write requests issued to the device to be served. This includes the time spent by the requests in queue and the time spent servicing them.
					
					#aqu-sz - The average queue length of the requests that were issued to the device.
					#	Note: In previous versions, this field was known as avgqu-sz.
					#svctm - The average service time (in milliseconds) for I/O requests that were issued to the device. Warning! Do not trust this field any more. This field will be removed in a future sysstat version.

					io_vals.append( [ columns[0], 'r/s', columns[1] ] )
					io_vals.append( [ columns[0], 'w/s', columns[2] ] )
					io_vals.append( [ columns[0], 'rMB/s', columns[3] ] )
					io_vals.append( [ columns[0], 'wMB/s', columns[4] ] )
					io_vals.append( [ columns[0], 'rrqm/s', columns[5] ] )
					io_vals.append( [ columns[0], 'wrqm/s', columns[6] ] )
					io_vals.append( [ columns[0], 'avgrq-sz', float(columns[12]) + float(columns[13]) ] 	#rareq-sz + wareq-sz
					io_vals.append( [ columns[0], 'avgqu-sz', columns[11] ] )	#aqu-sz
					io_vals.append( [ columns[0], 'await', float(columns[9]) + float(columns[10]) ] )
					io_vals.append( [ columns[0], 'svctm', columns[14] ] )
					io_vals.append( [ columns[0], '%util', columns[15] ] )

	cmd_netstat_t2 = subprocess.Popen('netstat -i',shell=True,stdout=subprocess.PIPE)
	write_network_vals( cmd_netstat_t2 )	
				
	cpu_vals_avg = []
	io_vals_avg = []
	network_vals_diff = []

	cpu_vals_avg.append( avg_param( '%user', cpu_vals ) )
	cpu_vals_avg.append( avg_param( '%nice',  cpu_vals ) )
	cpu_vals_avg.append( avg_param( '%system', cpu_vals ) )
	cpu_vals_avg.append( avg_param( '%iowait', cpu_vals ) )
	cpu_vals_avg.append( avg_param( '%steal', cpu_vals ) )
	cpu_vals_avg.append( avg_param( '%idle', cpu_vals ) )
	
	hdd_devices = get_devices( io_vals )
	network_devices = get_devices( network_vals )

	for device in network_devices:
		network_vals_diff.append( diff_param_by_device( device, 'RX-OK',  network_vals ) )
		network_vals_diff.append( diff_param_by_device( device, 'RX-ERR', network_vals ) )
		network_vals_diff.append( diff_param_by_device( device, 'RX-DRP', network_vals ) )
		network_vals_diff.append( diff_param_by_device( device, 'RX-OVR', network_vals ) )
		network_vals_diff.append( diff_param_by_device( device, 'TX-OK',  network_vals ) )
		network_vals_diff.append( diff_param_by_device( device, 'TX-ERR', network_vals ) )
		network_vals_diff.append( diff_param_by_device( device, 'TX-DRP', network_vals ) )		
		network_vals_diff.append( diff_param_by_device( device, 'TX-OVR', network_vals ) )		
		network_vals_diff.append( diff_param_per_sec_by_device( device, 'rx_bytes', network_vals, sleep_interval_os_stat_if_iostat_not_working ) )	#must be equal to iostat delay
		network_vals_diff.append( diff_param_per_sec_by_device( device, 'tx_bytes', network_vals, sleep_interval_os_stat_if_iostat_not_working ) )
		
	for device in hdd_devices:
		io_vals_avg.append( avg_param_by_device( device, 'rrqm/s', io_vals ) )
		io_vals_avg.append( avg_param_by_device( device, 'wrqm/s', io_vals ) )
		io_vals_avg.append( avg_param_by_device( device, 'r/s', io_vals ) )
		io_vals_avg.append( avg_param_by_device( device, 'w/s', io_vals ) )
		io_vals_avg.append( avg_param_by_device( device, 'rMB/s', io_vals ) )
		io_vals_avg.append( avg_param_by_device( device, 'wMB/s', io_vals ) )
		io_vals_avg.append( avg_param_by_device( device, 'avgrq-sz', io_vals ) )
		io_vals_avg.append( avg_param_by_device( device, 'avgqu-sz', io_vals ) )
		io_vals_avg.append( avg_param_by_device( device, 'await', io_vals ) )
		io_vals_avg.append( avg_param_by_device( device, 'svctm', io_vals ) )
		io_vals_avg.append( avg_param_by_device( device, '%util', io_vals ) )

	return [ cpu_vals_avg, io_vals_avg, network_vals_diff ]

def make_stat_mem_data():	
	result = []
	cmd = subprocess.Popen('cat /proc/meminfo | grep -e MemTotal: -e MemFree: -e "Active(file):" -e "Inactive(file):"' + \
		' -e Buffers: -e Dirty: -e Shmem: -e Slab: -e PageTables: -e SwapFree: -e SwapTotal: -e Cached: -e SwapCached: -e VmallocUsed: -e Inactive:',shell=True,stdout=subprocess.PIPE)
	list_begin = False
	for line in cmd.stdout:
		columns = line.decode('utf8').split()
		if len( columns ) == 3:
			result.append( [ re.findall("[\w\(\)]+", columns[0])[0], columns[1] ] )

	MemTotal = 0
	MemFree = 0
	Buffers = 0
	Cached = 0
	SwapCached = 0
	Slab = 0
	PageTables = 0

	for rec in result:
		if rec[ 0 ] == 'MemTotal':
			MemTotal = rec[ 1 ]
		if rec[ 0 ] == 'MemFree':
			MemFree = rec[ 1 ]
		if rec[ 0 ] == 'Buffers':
			Buffers = rec[ 1 ]
		if rec[ 0 ] == 'Cached':
			Cached = rec[ 1 ]
		if rec[ 0 ] == 'SwapCached':
			SwapCached = rec[ 1 ]
		if rec[ 0 ] == 'Slab':
			Slab = rec[ 1 ]
		if rec[ 0 ] == 'PageTables':
			PageTables = rec[ 1 ]

	result.append( [ 'AppMem', str( int(MemTotal) - int(MemFree) - int(Buffers) - int(Cached) - int(SwapCached) - int(Slab) - int(PageTables) ) ] )
	
	#AppMem + PageTables + Buffers + Shmem + Active(file) + Inactive(file) + Slab  + MemFree = MemTotal
	#Cached = Shmem + Active(file) + Inactive(file)
	
	return result

def make_stat_disk_data():	
	result = []
	cmd = subprocess.Popen('df',shell=True,stdout=subprocess.PIPE)
	list_begin = False
	for line in cmd.stdout:
		columns = line.decode('utf8').split()
		if len( columns ) == 6 and columns[0] != 'Filesystem':
			result.append( columns ) 
	return result	

def os_stat_collect():
	sys_stat_db = None
	
	while True:
		data_collected = False
		try:	
			logger.log( 'os_stat_collect iteration started!', "Info" )	
			iostat_data_res = make_iostat_data()
			stat_mem_data_res = make_stat_mem_data()
			stat_disk_data_res = make_stat_disk_data()
			logger.log( 'os_stat_collect collected!', "Info" )
			data_collected = True
		except Exception as e:
			logger.log( "os_stat_collect error: " + str( e ), "Error" )
			time.sleep(sleep_interval_on_exception)

		if not data_collected:
			continue

		try:
			sys_stat_db = postgresql.open( sys_stat_conn_str )
			init_sys_stat( sys_stat_db ) 
			
			stm = sys_stat_db.prepare("""INSERT INTO psc_os_stat( param_id, val ) VALUES ( (select psc_get_param( $1 )), $2 );""")	
			
			with sys_stat_db.xact():			
				for rec in stat_mem_data_res:
					stm.first( rec[0], rec[1] )

				if len( iostat_data_res ) > 0:
					for rec in iostat_data_res[0]:
						stm.first( rec[0], rec[1] )

					stm = sys_stat_db.prepare("""INSERT INTO psc_os_stat( device_id, param_id, val ) VALUES ( (select psc_get_device( $1, 'hdd' )), (select psc_get_param( $2 )), round($3, 3) );""")	 
					for rec in iostat_data_res[1]:
						stm.first( str( rec[0] ), str( rec[1] ), rec[2] )

					stm = sys_stat_db.prepare("""INSERT INTO psc_os_stat( device_id, param_id, val ) VALUES ( (select psc_get_device( $1, 'network' )), (select psc_get_param( $2 )), round($3, 3) );""")	 
					for rec in iostat_data_res[2]:
						stm.first( str( rec[0] ), str( rec[1] ), rec[2] )
				
				stm = sys_stat_db.prepare("""INSERT INTO psc_os_stat( device_id, param_id, val ) VALUES ( (select psc_get_device( $1, 'df' )), (select psc_get_param( $2 )), round($3, 3) );""")	 
				for rec in stat_disk_data_res:
					stm.first( str( rec[5] ), str( 'disk_size' ), rec[1] )
					stm.first( str( rec[5] ), str( 'disk_size_used' ), rec[2] )
					stm.first( str( rec[5] ), str( 'disk_size_avail' ), rec[3] )
					
			logger.log('os_stat_collect iteration finished! Sleep on ' + str( sleep_interval_os_stat ) + " seconds...", "Info" )
		except Exception as e:
			logger.log( "Connection sys_stat_db error: " + str( e ), "Error" )
			time.sleep(sleep_interval_on_exception)
		finally:
			if sys_stat_db is not None:
				if not sys_stat_db.closed:
					sys_stat_db.close()

#=======================================================================================================
try:
	sys_stat_db = postgresql.open( sys_stat_conn_str )
	init_sys_stat_node( sys_stat_db )
except Exception as e:
	logger.log( "Connection sys_stat_conn_str error: " + str( e ), "Error" )
	time.sleep(sleep_interval_on_exception)
finally:
	if sys_stat_db is not None:
		sys_stat_db.close()
#=======================================================================================================

if collect_pg_sys_stat:
	pg_sys_stat_snapshot_thread = Thread( target=pg_sys_stat_snapshot, args=[] )
	pg_sys_stat_snapshot_thread.start()
	pg_single_db_sn_thread = Thread( target=pg_single_db_sn, args=[] )
	pg_single_db_sn_thread.start()
	logger.log( '-------> pg_sys_stat activated!', "Info" )

if collect_pg_conn_snapshot:
	pg_conn_snapshot_thread = Thread( target=pg_conn_snapshot, args=[] )
	pg_conn_snapshot_thread.start()
	logger.log( '-------> pg_conn_snapshot activated!', "Info" )	

if collect_os_stat:	
	os_stat_thread = Thread( target=os_stat_collect, args=[] )
	os_stat_thread.start()
	logger.log( '-------> os_stat activated!', "Info" )

logger.log( "=======> pg_stat_sys runned!", "Info" )