print('healer')
import subprocess

def auto_heal(status, diag):
    if not diag:
        return None

    # 恢复相机
    if "Camera" in diag:
        subprocess.call("sudo systemctl restart camera.service", shell=True)
        return "Camera pipeline restarted"

    # 恢复 GPU 模型
    if "GPU" in diag:
        subprocess.call("sudo systemctl restart ai.service", shell=True)
        return "AI model restarted"

    # 内存泄露恢复
    if "Memory" in diag:
        subprocess.call("sudo systemctl restart edgeops", shell=True)
        return "Rebooted EdgeOps due to memory issue"

    return None

