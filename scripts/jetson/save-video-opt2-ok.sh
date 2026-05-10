#!/bin/bash

# 定义通道列表（支持多路）
CAMERAS=(
  "rtsp://admin:gosuncn2024@192.168.1.55:554/cam/realmonitor?channel=1&subtype=0"
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
    rtspsrc location="$RTSP_URL" ! \
    rtph264depay ! \
    h264parse ! \
    nvv4l2decoder ! \
    nvv4l2h264enc ! \
    h264parse ! \
    queue ! \
    splitmuxsink muxer=mp4mux \
      location=video_${IP_ADDRESS}_%05d.h264 \
      max-size-time=300000000000 2>&1 >> /tmp/video.log &  # 每5分钟分割（300秒）
done

# 等待所有后台任务
wait
