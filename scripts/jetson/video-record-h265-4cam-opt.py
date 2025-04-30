import subprocess
import time
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ffmpeg_recorder.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def run_ffmpeg(rtsp_url, output_prefix):
    """运行FFmpeg录制单路RTSP流"""
    SEGMENT_DURATION = 10 * 60  # 分段时长（秒）

    command = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',        # 强制TCP传输
        '-i', rtsp_url,                  # 输入RTSP流
        '-c:v', 'libx265',               # 视频编码为H.265
        '-preset', 'medium',             # 编码速度与质量平衡
        '-crf', '28',                    # 恒定质量因子
        '-c:a', 'aac',                   # 音频转码为AAC
        '-f', 'segment',                # 分段输出
        '-segment_format', 'mp4',        # 分段文件格式为MP4
        '-segment_list_type', 'csv',    # 使用CSV记录切割点
        '-segment_time', str(SEGMENT_DURATION),  # 分段时长
        '-reset_timestamps', '1',        # 重置时间戳
        '-strftime', '1',               # 使用时间戳命名文件
        '-force_key_frames', f'expr:gte(t,n_forced*{SEGMENT_DURATION})',  # 强制关键帧
        '-flush_packets', '1',           # 及时刷新写入
        '-movflags', '+faststart',       # 将moov atom移动到文件开头（适用于MP4）
        f'{output_prefix}_%Y%m%d%H%M%S.mp4'  # 输出文件名
    ]

    # 启动FFmpeg进程
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    return process

def monitor_process(process, camera_name):
    """监控FFmpeg进程状态，处理异常退出"""
    while True:
        retcode = process.poll()  # 检查进程是否退出
        if retcode is not None:
            # 进程退出
            stderr = process.stderr.read()
            logging.error(f"{camera_name} FFmpeg process exited with code {retcode}.")
            logging.error(f"Error output: {stderr}")
            break
        time.sleep(5)  # 每隔5秒检查一次

def main():
    # 定义4路相机的RTSP URL和输出文件名前缀
    cameras = [
        {'url': 'rtsp://admin:gosuncn2024@192.168.8.11:554/cam/realmonitor?channel=1&subtype=0', 'prefix': 'cam1'},
        {'url': 'rtsp://admin:gosuncn2024@192.168.8.12:554/cam/realmonitor?channel=1&subtype=0', 'prefix': 'cam2'},
        {'url': 'rtsp://admin:gosuncn2024@192.168.8.13:554/cam/realmonitor?channel=1&subtype=0', 'prefix': 'cam3'},
        {'url': 'rtsp://admin:gosuncn2024@192.168.8.14:554/cam/realmonitor?channel=1&subtype=0', 'prefix': 'cam4'},
    ]

    processes = {}
    try:
        # 启动4个FFmpeg进程
        for camera in cameras:
            camera_name = camera['prefix']
            logging.info(f"Starting FFmpeg for {camera_name}...")
            process = run_ffmpeg(camera['url'], camera_name)
            processes[camera_name] = process

        # 监控进程状态
        while True:
            for camera_name, process in processes.items():
                if process.poll() is not None:  # 如果进程退出
                    logging.warning(f"{camera_name} FFmpeg process crashed. Restarting...")
                    processes[camera_name] = run_ffmpeg(camera['url'], camera_name)
            time.sleep(10)  # 每隔10秒检查一次

    except KeyboardInterrupt:
        logging.info("Stopping FFmpeg processes...")
        for process in processes.values():
            process.terminate()
        logging.info("All processes stopped.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        # 确保所有进程终止
        for process in processes.values():
            process.terminate()

if __name__ == '__main__':
    main()