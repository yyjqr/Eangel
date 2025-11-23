print('diagnose')
import subprocess, time

log_keywords = {
    "GPU": ["Xid", "GPU fault", "ERROR"],
    "Camera": ["device lost", "no frame"],
    "Memory": ["oom", "out of memory"]
}

def diagnose_logs():
    logs = subprocess.getoutput("dmesg | tail -n 30")
    results = []

    for key, words in log_keywords.items():
        for w in words:
            if w in logs:
                results.append(f"{key} issue: {w}")

    return "; ".join(results) if results else None

