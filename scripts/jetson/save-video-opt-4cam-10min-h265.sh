#!/bin/bash

# 定义通道列表（支持多路）
CAMERAS=(
  "rtsp://admin:gosuncn2024@192.168.22.11:554/cam/realmonitor?channel=1&subtype=0"
   "rtsp://admin:gosuncn2024@192.168.22.12:554/cam/realmonitor?channel=1&subtype=0"
    "rtsp://admin:gosuncn2024@192.168.22.13:554/cam/realmonitor?channel=1&subtype=0"
     "rtsp://admin:gosuncn2024@192.168.22.14:554/cam/realmonitor?channel=1&subtype=0"
)

# 循环启动每路相机的录制任务
CHANNEL=0
for CAMERA in "${CAMERAS[@]}"; do
  # 提取RTSP地址和通道名
  RTSP_URL=$(echo $CAMERA | awk '{print $1}')
  # 使用正则表达式提取IP地址
  # 解析IP地址,:分隔，取第4个
  IP_ADDRESS=$(echo "$RTSP_URL" | awk -F'[@:]' '{print $4}')

echo $IP_ADDRESS
# 检查是否成功解析IP
if [[ -z "$IP_ADDRESS" ]]; then
  echo "Failed to parse IP address from RTSP URL."
  exit 1
fi

mkdir -p /mnt/share/camData
mkdir -p /mnt/share/camData/${IP_ADDRESS}
# 生成带IP地址和日期时间的文件名模板
#FILENAME_TEMPLATE="video_${IP_ADDRESS}_%Y%m%d_%H%M%S.h264"
curTime=`date '+%Y-%m-%d_%H%M%S'`
echo $curTime
#FILENAME_TEMPLATE="video_${IP_ADDRESS}_${curTime}.h264"

echo $FILENAME_TEMPLATE  
# 生成带日期和通道名的文件名模板
  #FILENAME_TEMPLATE="video_${IP_ADDRESS}_%Y%m%d_%H%M%S.h264"

  # 启动GStreamer管道（后台运行）
  gst-launch-1.0 -e \
    rtspsrc location="$RTSP_URL" protocols=tcp ! \
    rtph265depay ! \
    h265parse ! \
    nvv4l2decoder ! \
    nvv4l2h265enc ! \
    h265parse ! \
    queue ! \
    splitmuxsink muxer=mp4mux \
      location=/mnt/share/camData/${IP_ADDRESS}/video_${IP_ADDRESS}_${curTime}_%05d.h265 \
      max-size-time=600000000000 2>&1 >> ./video.log &  # 每10分钟分割（600秒）
done

# 等待所有后台任务
wait
