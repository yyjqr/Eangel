# 前台运行
## python3 record.py
# 后台运行
## nohup python3 record.py > recorder.log 2>&1 &

# 安装基础编译工具
# sudo apt-get install -y build-essential yasm cmake libtool pkg-config

# 安装Python3环境
# sudo apt-get install -y python3 python3-pip
# pip3 install --upgrade pip

import subprocess
import time
import datetime
import os
import signal

RTSP_URL = "rtsp://admin:gosuncn2024@192.168.8.101:554/cam/realmonitor?channel=1&subtype=0"
SEGMENT_DURATION = 3600  # 1小时分割
RECONNECT_INTERVAL = 5    # 重试间隔(秒)

def run_ffmpeg():
    """运行带I帧切割的FFmpeg命令"""
    return subprocess.Popen([
        'ffmpeg',
        '-rtsp_transport', 'tcp',        # 强制TCP传输
        '-i', RTSP_URL,
        '-c:v', 'copy',                  # 视频流直接复制
        '-c:a', 'aac',                   # 音频转码为AAC
        '-f', 'segment',
        '-segment_format', 'mp4',
        '-segment_list_type', 'csv',     # 使用CSV记录切割点
        '-segment_time', str(SEGMENT_DURATION),
        '-reset_timestamps', '1',
        '-strftime', '1',
        '-segment_clocktime_offset', '1',  # 对齐系统时钟
        '-segment_atclocktime', '1',       # 整点切割
        '-force_key_frames', 'expr:gte(t,n_forced*3600)',  # 强制关键帧
        '-flush_packets', '1',            # 及时刷新写入
        '-movflags', '+faststart',        # 将moov atom移动到文件开头
        'cam%Y%m%d%H%M%S.mp4'
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

def main():
    while True:
        try:
            print(f"🟢 开始录制到文件")
            ffmpeg_process = run_ffmpeg()
            
            # 监控FFmpeg输出
            while True:
                output = ffmpeg_process.stdout.readline()
                if not output and ffmpeg_process.poll() is not None:
                    break
                if output:
                    print(output.decode().strip())
                    
            # 检测退出状态
            if ffmpeg_process.returncode != 0:
                print(f"🔴 FFmpeg异常退出(代码:{ffmpeg_process.returncode})，尝试重连...")
            
        except KeyboardInterrupt:
            print("\n🛑 用户终止操作")
            ffmpeg_process.send_signal(signal.SIGINT)
            ffmpeg_process.wait()
            break
        except Exception as e:
            print(f"❌ 发生异常: {str(e)}")
        
        # 等待重试
        print(f"⏳ {RECONNECT_INTERVAL}秒后尝试重新连接...")
        time.sleep(RECONNECT_INTERVAL)

if __name__ == "__main__":
    main()
