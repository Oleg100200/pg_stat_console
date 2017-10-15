#!/bin/sh

PYTHON='/usr/local/bin/python3.6' 
PSC_UNIT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PSC_PATH="$(dirname "$PSC_UNIT_PATH")"

if [[ $(ps --no-headers -o comm 1) != "systemd" ]]; then
	echo -e "\ninit is not supported"
	exit
fi

for f in "$PSC_UNIT_PATH"/pg_stat_*example; do if [[ -f "$f" ]]; then
	if [[ $f == *".service"* ]]; then
		NEW_NAME="${f%.*}"
		cp $f $NEW_NAME
		echo "Processing " $NEW_NAME
		sed -i "s|PYTHON|$PYTHON|g" $NEW_NAME
		sed -i "s|PSC_PATH|$PSC_PATH|g" $NEW_NAME
		cp $NEW_NAME /usr/lib/systemd/system
		chmod 664 /usr/lib/systemd/system/$(basename "$NEW_NAME")
	else
		echo -e "\nWrong input file " $f
	fi
fi; done

systemctl daemon-reload
echo -e "\nsystemctl has been reloaded"