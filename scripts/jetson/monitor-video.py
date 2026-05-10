import os
import time
import subprocess

# 要监控的脚本路径
SCRIPT_PATH = "/mnt/share/camData02027/record_rtsp.sh"

# 日志文件路径
LOG_FILE = "/tmp/monitor.log"

def is_script_running():
    """检查脚本是否正在运行"""
    try:
        # 使用 pgrep 查找脚本的进程
        result = subprocess.run(["pgrep", "-f", SCRIPT_PATH], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return bool(result.stdout)
    except Exception as e:
        print(f"Error checking script status: {e}")
        return False

def start_script():
    """启动脚本"""
    try:
        # 使用 subprocess.Popen 启动脚本（后台运行）
        subprocess.Popen([SCRIPT_PATH], stdout=open(LOG_FILE, "a"), stderr=subprocess.STDOUT)
        print(f"Started script: {SCRIPT_PATH}")
    except Exception as e:
        print(f"Error starting script: {e}")

def main():
    # 监控间隔（秒）
    MONITOR_INTERVAL = 60

    while True:
        if not is_script_running():
            print(f"Script is not running. Restarting...")
            start_script()
        else:
            print(f"Script is running.")

        # 等待一段时间后再次检查
        time.sleep(MONITOR_INTERVAL)

if __name__ == "__main__":
    main()
