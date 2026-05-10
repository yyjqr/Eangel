#!/bin/bash
curTime=`date '+%Y-%m-%d_%H%M%S'`
echo $curTime
sudo /tmp/mec-fal-save-test 1
sudo mkdir -p /mnt/share/sensorsData-WH$1
##lidar 
sudo tcpdump  -i eth1 src host 192.168.8.102 -w /mnt/share/sensorsData-WH$1/lidar_$(date +'%Y-%m-%d-%H%M%S').pcap -v
