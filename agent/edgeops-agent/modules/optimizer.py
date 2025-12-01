print('optimizer')
import subprocess
import json

def auto_optimize(status_json):
    status = json.loads(status_json)

    # 自动切换模型
    if status["cpu"] > 90:
        subprocess.call("sudo nvpmodel -m 1", shell=True)
        return "Switched to low-power mode"

    if status["mem"] > 80:
        subprocess.call("sudo systemctl restart ai.service", shell=True)
        return "Restart AI to clear memory"

    return None

