#!/bin/sh

PYTHON='/usr/local/bin/python3.6' 
PSC_PATH_INSTALL=$PWD
PSC_PATH="$(dirname "$PSC_PATH_INSTALL")"

cd unit
for f in pg_stat_*; do if [[ -f "$f" ]]; then
	if [[ $f == *".service"* ]]; then
		echo "Processing " $f
		sed -i "s|PYTHON|$PYTHON|g" $f
		sed -i "s|PSC_PATH|$PSC_PATH|g" $f
		cp $PSC_PATH_INSTALL/unit/$f /usr/lib/systemd/system
		chmod 664 /usr/lib/systemd/system/$f
	else
		echo -e "\nWrong input file " $f
	fi
fi; done

systemctl daemon-reload

echo -e "\nsystemctl has been reloaded"