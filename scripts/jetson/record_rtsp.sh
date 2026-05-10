#!/bin/bash
cd /mnt/share/camData02027
echo "record data"
curTime=`date '+%Y-%m-%d_%H%M%S'`
echo $curTime

sudo  python video-record.py 
