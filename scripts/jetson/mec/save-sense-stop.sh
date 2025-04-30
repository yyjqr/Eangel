#!/bin/bash
sudo /tmp/mec-fal-save-test 0
sleep 3
killall tcpdump
sudo mv /mnt/share/mec-app /mnt/share/sensorsData-WH$1/mec-app-$(date +'%Y-%m-%d-%H-%M-%S')-$1

