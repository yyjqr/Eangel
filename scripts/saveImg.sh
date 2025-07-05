#!/bin/bash
#timeout 3 ffmpeg -i "rtsp://admin:xxx@192.168.xx:554/cam/realmonitor?channel=1&subtype=0" -y -f image2 -r 3/1 /tmp/img-2025-02-02-%03d.jpg

ffmpeg -t 10 -i "rtsp://xx:xx@172.xx:554/Streaming/Channels/103" -y -f image2 -r 1/5 -strftime 1 /tmp/"cam_%Y%m%d_%H%M%S.jpg"
ffmpeg -t 10 -i "rtsp://xx:xx@172.xx:554/Streaming/Channels/103" -y -f image2 -r 1/5 -strftime 1 /tmp/"cam_hk__%Y%m%d_%H%M%S.jpg"
