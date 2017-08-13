#!/bin/sh

PYTHON='/usr/local/bin/python3.6' 
PSC_PATH_INSTALL=$PWD
PSC_PATH="$(dirname "$PSC_PATH_INSTALL")"

for f in pg_stat_*; do if [[ -f "$f" ]]; then
	sed -i "s|PYTHON|$PYTHON|g" $f
	sed -i "s|PSC_PATH|$PSC_PATH|g" $f
	cp $PSC_PATH_INSTALL/$f /usr/lib/systemd/system
	chmod 664 /usr/lib/systemd/system/$f
fi; done

systemctl daemon-reload