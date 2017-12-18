strindex() {
  x="${1%%$2*}"
  [[ "$x" = "$1" ]] && echo -1 || echo "${#x}"
}

get_scalar()
{
	results=($(su -l postgres -c "psql -A -t -p '${db_port}' -h 127.0.0.1 -U postgres -d $1 -c \"$2\""))
	fld1=`echo ${results[0]} | awk -F'|' '{print $1}'`
	echo ${fld1}
}

get_pg_version()
{
	pg_version=$(get_scalar "postgres" "SHOW server_version_num;")

	if [ $current_os == "RHEL" ]; then
		if [ "$pg_version" -ge "90200" ] && [ "$pg_version" -lt "90300" ]; then
			pg_service_name="postgresql-9.2"
			pg_dir_bin="/usr/pgsql-9.2/bin"
		fi
		if [ "$pg_version" -ge "90300" ] && [ "$pg_version" -lt "90400" ]; then
			pg_service_name="postgresql-9.3"
			pg_dir_bin="/usr/pgsql-9.3/bin"
		fi
		if [ "$pg_version" -ge "90400" ] && [ "$pg_version" -lt "90500" ]; then
			pg_service_name="postgresql-9.4"
			pg_dir_bin="/usr/pgsql-9.4/bin"
		fi
		if [ "$pg_version" -ge "90500" ] && [ "$pg_version" -lt "90600" ]; then
			pg_service_name="postgresql-9.5"
			pg_dir_bin="/usr/pgsql-9.5/bin"
		fi
		if [ "$pg_version" -ge "90600" ] && [ "$pg_version" -lt "100000" ]; then
			pg_service_name="postgresql-9.6"
			pg_dir_bin="/usr/pgsql-9.6/bin"
		fi		
		if [ "$pg_version" -ge "100000" ] && [ "$pg_version" -lt "110000" ]; then
			pg_service_name="postgresql-10"
			pg_dir_bin="/usr/pgsql-10/bin"
		fi
	fi

	if [ $current_os == "Ubuntu" ]; then
		if [ "$pg_version" -ge "90200" ] && [ "$pg_version" -lt "90300" ]; then
			pg_service_name="postgresql@9.2-main"
			pg_dir_bin="/usr/lib/postgresql/9.2/bin"
		fi
		if [ "$pg_version" -ge "90300" ] && [ "$pg_version" -lt "90400" ]; then
			pg_service_name="postgresql@9.3-main"
			pg_dir_bin="/usr/lib/postgresql/9.3/bin"
		fi
		if [ "$pg_version" -ge "90400" ] && [ "$pg_version" -lt "90500" ]; then
			pg_service_name="postgresql@9.4-main"
			pg_dir_bin="/usr/lib/postgresql/9.4/bin"
		fi
		if [ "$pg_version" -ge "90500" ] && [ "$pg_version" -lt "90600" ]; then
			pg_service_name="postgresql@9.5-main"
			pg_dir_bin="/usr/lib/postgresql/9.5/bin"
		fi
		if [ "$pg_version" -ge "90600" ] && [ "$pg_version" -lt "100000" ]; then
			pg_service_name="postgresql@9.6-main"
			pg_dir_bin="/usr/lib/postgresql/9.6/bin"
		fi
		if [ "$pg_version" -ge "100000" ] && [ "$pg_version" -lt "110000" ]; then
			pg_service_name="postgresql@10-main"
			pg_dir_bin="/usr/lib/postgresql/10/bin"
		fi
	fi
}

run_pg_configure()
{
	tune_core_params=()

	tune_core_params+=("shared_buffers = 1GB")
	tune_core_params+=("temp_buffers = 256MB")
	tune_core_params+=("work_mem = 256MB")
	tune_core_params+=("maintenance_work_mem = 256MB")

	tune_core_params+=("vacuum_cost_limit = 5000")

	tune_core_params+=("autovacuum = on")
	tune_core_params+=("autovacuum_max_workers = 4")
	tune_core_params+=("autovacuum_naptime = 1min")
	tune_core_params+=("autovacuum_vacuum_threshold = 10000")
	tune_core_params+=("autovacuum_analyze_threshold = 5000")
	tune_core_params+=("autovacuum_vacuum_scale_factor = 0.4")
	tune_core_params+=("autovacuum_analyze_scale_factor = 0.2")
	tune_core_params+=("autovacuum_vacuum_cost_delay = 10ms")
	tune_core_params+=("autovacuum_vacuum_cost_limit = 5000")

	tune_core_params+=("synchronous_commit = off")
	tune_core_params+=("checkpoint_timeout = 10min")
	tune_core_params+=("max_wal_size = 1GB")
	tune_core_params+=("min_wal_size = 80MB")
	tune_core_params+=("checkpoint_completion_target = 0.9")

	tune_core_params+=("bgwriter_delay = 5000ms")
	tune_core_params+=("bgwriter_lru_maxpages = 1000")
	tune_core_params+=("bgwriter_lru_multiplier = 7.0")

	tune_core_params+=("default_statistics_target = 1000")
	tune_core_params+=("statement_timeout = 3600000 ")
	tune_core_params+=("lock_timeout = 600000 ")


	tune_core_params+=("shared_preload_libraries = 'pg_stat_statements,auto_explain'")
	tune_core_params+=("pg_stat_statements.max = 1000")
	tune_core_params+=("pg_stat_statements.track = all")
	
	tune_core_params+=("auto_explain.log_min_duration = '3s'")
	tune_core_params+=("auto_explain.log_analyze = true")
	tune_core_params+=("auto_explain.log_verbose = true")
	tune_core_params+=("auto_explain.log_buffers = true")
	tune_core_params+=("auto_explain.log_format = text")
	
	tune_core_params+=("log_destination = 'csvlog'")
	tune_core_params+=("logging_collector = on")
	tune_core_params+=("log_directory = 'pg_log'")
	tune_core_params+=("log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'")
	tune_core_params+=("log_truncate_on_rotation = on")
	tune_core_params+=("log_rotation_age = 1d")
	tune_core_params+=("log_rotation_size = 100MB")
	tune_core_params+=("log_min_error_statement = error")
	tune_core_params+=("log_min_duration_statement = 3000")
	tune_core_params+=("log_duration = off")
	tune_core_params+=("log_line_prefix = '%t %a'")
	tune_core_params+=("log_lock_waits = on")
	tune_core_params+=("log_statement = 'ddl'")
	tune_core_params+=("log_temp_files = -1")
	tune_core_params+=("log_timezone = 'Europe/Moscow'")
	
	tune_core_params+=("track_activities = on")
	tune_core_params+=("track_counts = on")
	tune_core_params+=("track_io_timing = on")
	tune_core_params+=("track_functions = pl")
	tune_core_params+=("track_activity_query_size = 2048")

	mapfile -t source_config < $pg_config
	
	matches_count=0
	for line in "${source_config[@]}"
	do
		for tune_core_param in "${tune_core_params[@]}"
		do
			if [[ $line == $tune_core_param ]]; then
				matches_count+=1
			fi
			if [[ $matches_count -ge 5 ]]; then
				echo -e ${pg_config} 'already configured'
				echo
				return
			fi
		done
	done
	
	cp $pg_config ${pg_config}.$(date '+%Y%m%d_%H%M%S')
	new_config=()
	tune_core_params_done=()
	
	for line in "${source_config[@]}"
	do
		param_name_tmp=($line)
		param_name=${param_name_tmp[0]}
		found=0
		if [[ !($param_name == *"#"*) ]] && [ ${#param_name} -ge 2 ]; then
			#check active params
			for tune_core_param in "${tune_core_params[@]}"
			do
				tune_core_param_name_tmp=($tune_core_param)
				tune_core_param_name=${tune_core_param_name_tmp[0]}
				if [[ $tune_core_param_name == "$param_name" ]]; then
					new_config+=("#$line")
					new_config+=("$tune_core_param")
					tune_core_params_done+=("$tune_core_param")
					found=1
				fi
			done
			if [[ $found == 0 ]]; then
				new_config+=("$line")
			fi
		else
			new_config+=("$line")
		fi
	done
	
	for line in "${source_config[@]}"
	do
		param_name_tmp=($line)
		param_name=${param_name_tmp[0]}
		
		if [[ $param_name == *"#"* ]] && [ ${#param_name} -ge 2 ]; then
			#check commented params
			comment_pos=$(strindex "$param_name" "#")
			uncommented_param_name="${param_name:1}"
			
			if [ $comment_pos == 0 ] ; then
				found=0
				for tune_core_param_done in "${tune_core_params_done[@]}"
				do
					tune_core_param_name_tmp=($tune_core_param_done)
					tune_core_param_name=${tune_core_param_name_tmp[0]}
					if [[ $uncommented_param_name == $tune_core_param_name ]]; then
						found=1
						break
					fi
				done

				if [[ $found == 0 ]]; then
					for tune_core_param in "${tune_core_params[@]}"
					do
						tune_core_param_name_tmp=($tune_core_param)
						tune_core_param_name=${tune_core_param_name_tmp[0]}
						if [[ $uncommented_param_name == $tune_core_param_name ]]; then
							new_config+=("$tune_core_param")
							tune_core_params_done+=("$tune_core_param")
						fi
					done
				fi
			fi
		fi
	done
	
	for check_param in "${tune_core_params[@]}"
	do
		found=0
		check_param_tmp=($check_param)
		check_param_tmp=${check_param_tmp[0]}
		for added_param in "${tune_core_params_done[@]}"
		do
			added_param_tmp=($added_param)
			added_param_tmp=${added_param_tmp[0]}
			if [[ $check_param_tmp == "$added_param_tmp" ]]; then
				found=1
			fi
		done
		
		if [[ $found == 0 ]]; then
			new_config+=("$check_param")
		fi
	done
	
	printf "%s\n" "${new_config[@]}" > ${pg_config}
	
	systemctl daemon-reload
	systemctl restart $pg_service_name
}
