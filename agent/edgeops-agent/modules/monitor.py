print('monitor')
import psutil, subprocess, json, os
import time

def read_tegrastats():
    out = subprocess.getoutput("tegrastats --interval 1000 --count 1")
    return out

def camera_ok():
    out = subprocess.getoutput("v4l2-ctl --list-devices")
    return "Cannot" not in out

def collect_status():
    return json.dumps({
        "cpu": psutil.cpu_percent(),
        "mem": psutil.virtual_memory().percent,
        "gpu_raw": read_tegrastats(),
        "camera_ok": camera_ok(),
        "timestamp": time.time()
    })

