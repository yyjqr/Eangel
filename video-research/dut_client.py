"""
DUT 板端通信客户端
支持：Telnet（BusyBox）/ SSH（Paramiko）/ 串口（pyserial）
资源受限板端无需安装 Python/SSH，仅需 BusyBox 自带的 nc + telnetd
"""

import socket
import threading
import time
import os
import re
try:
    import pexpect
    HAS_PEXPECT = True
except ImportError:
    HAS_PEXPECT = False

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


class DUTClient:
    """统一 DUT 控制接口（自动选择 Telnet/SSH/Serial）"""

    def __init__(self, cfg: dict):
        self.cfg     = cfg
        self.name    = cfg.get("name", "DUT")
        self.ip      = cfg.get("ip", "")
        self.protocol= cfg.get("protocol", "telnet")
        self._conn   = None

    # ── 连接管理 ─────────────────────────────────────────
    def connect(self):
        if self.protocol == "telnet":
            self._conn = _TelnetConn(self.cfg)
        elif self.protocol == "ssh":
            self._conn = _SSHConn(self.cfg)
        elif self.protocol == "serial":
            self._conn = _SerialConn(self.cfg)
        else:
            raise ValueError(f"未知协议: {self.protocol}")
        self._conn.connect()

    def close(self):
        if self._conn:
            self._conn.close()

    # ── 命令执行 ─────────────────────────────────────────
    def exec(self, cmd: str, timeout: int = 30) -> str:
        """执行命令并返回 stdout 字符串"""
        return self._conn.exec(cmd, timeout)

    def exec_bg(self, cmd: str):
        """后台执行（不等待返回，用于长时间采集）"""
        self._conn.exec(cmd + " &", timeout=3)

    # ── 系统状态查询 ──────────────────────────────────────
    def get_cpu_usage(self) -> float:
        """返回整体 CPU 占用 %（兼容 /proc/stat BusyBox）"""
        try:
            out1 = self.exec("cat /proc/stat | head -1")
            time.sleep(0.5)
            out2 = self.exec("cat /proc/stat | head -1")
            vals1 = list(map(int, re.findall(r'\d+', out1)))
            vals2 = list(map(int, re.findall(r'\d+', out2)))
            idle1, total1 = vals1[4], sum(vals1[1:])
            idle2, total2 = vals2[4], sum(vals2[1:])
            d_idle  = idle2  - idle1
            d_total = total2 - total1
            return round((1 - d_idle / max(d_total, 1)) * 100, 1)
        except Exception:
            return -1.0

    def get_mem_free_mb(self) -> float:
        """返回空闲内存 MB"""
        try:
            out = self.exec("cat /proc/meminfo | grep MemAvailable")
            val = int(re.search(r'\d+', out).group())
            return round(val / 1024, 1)
        except Exception:
            return -1.0

    def get_cpu_temp(self) -> float:
        """返回 CPU 温度 °C（多平台路径探测）"""
        paths = [
            "cat /sys/class/thermal/thermal_zone0/temp",
            "cat /sys/devices/virtual/thermal/thermal_zone0/temp",
        ]
        for p in paths:
            try:
                out = self.exec(p)
                val = int(re.search(r'\d+', out).group())
                return round(val / 1000.0, 1)
            except Exception:
                continue
        return -1.0

    def get_dmesg_tail(self, lines: int = 50) -> str:
        return self.exec(f"dmesg | tail -n {lines}", timeout=5)

    # ── 文件传输（nc 推流，不依赖 /tmp 大文件）────────────
    def push_file_via_nc(self, remote_path: str, server_ip: str, port: int):
        """板端用 nc 将文件推送到服务器（零拷贝，省内存）"""
        self.exec_bg(f"nc {server_ip} {port} < {remote_path}")

    def stream_capture_via_nc(self, capture_cmd: str, server_ip: str, port: int):
        """
        直接流式管道：板端 | nc 推流，不落盘到板端 /tmp
        capture_cmd 末尾需输出到 stdout，例如:
          v4l2-ctl ... --stream-to=- 或 cat /dev/xxx
        """
        cmd = f"{capture_cmd} | nc {server_ip} {port} &"
        self.exec(cmd, timeout=3)


class _ServerReceiver:
    """服务器端 TCP 接收器（在后台线程接收板端 nc 推来的数据）"""

    def __init__(self, port: int, save_path: str, timeout: int = 15):
        self.port      = port
        self.save_path = save_path
        self.timeout   = timeout
        self._ok       = False
        self._thread   = None

    def start(self):
        """启动后台接收线程"""
        self._thread = threading.Thread(target=self._recv, daemon=True)
        self._thread.start()

    def wait(self) -> bool:
        """等待接收完成，返回是否成功"""
        if self._thread:
            self._thread.join(timeout=self.timeout + 2)
        return self._ok

    def _recv(self):
        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", self.port))
                s.listen(1)
                s.settimeout(self.timeout)
                conn, _ = s.accept()
                conn.settimeout(5.0)
                with open(self.save_path, "wb") as f:
                    while True:
                        data = conn.recv(65536)
                        if not data:
                            break
                        f.write(data)
                conn.close()
                self._ok = True
        except Exception:
            self._ok = False


# ═══════════════════════════════════════════
# 底层协议实现
# ═══════════════════════════════════════════

class _TelnetConn:
    def __init__(self, cfg):
        self.ip       = cfg["ip"]
        self.user     = cfg.get("user", "root")
        self.password = cfg.get("password", "")
        self.port     = cfg.get("port", 23)
        self.timeout  = cfg.get("timeout", 10)
        self._s       = None

    def connect(self):
        if not HAS_PEXPECT:
            raise ImportError("请安装 pexpect: pip install pexpect")
        cmd = f"telnet {self.ip} {self.port}"
        self._s = pexpect.spawn(cmd, timeout=self.timeout, encoding="utf-8")
        idx = self._s.expect(["login:", "Login:", r"#\s*", pexpect.TIMEOUT], timeout=15)
        if idx in (0, 1):
            self._s.sendline(self.user)
            pidx = self._s.expect(["Password:", r"#\s*", pexpect.TIMEOUT])
            if pidx == 0:
                self._s.sendline(self.password)
                self._s.expect(r"#\s*")
        elif idx == 3:
            raise ConnectionError(f"Telnet 连接超时: {self.ip}")

    def exec(self, cmd: str, timeout: int = 30) -> str:
        self._s.sendline(cmd)
        self._s.expect(r"#\s*", timeout=timeout)
        return self._s.before.strip()

    def close(self):
        if self._s:
            try:
                self._s.sendline("exit")
                self._s.close()
            except Exception:
                pass


class _SSHConn:
    def __init__(self, cfg):
        self.ip       = cfg["ip"]
        self.user     = cfg.get("user", "root")
        self.password = cfg.get("password", "")
        self.port     = cfg.get("port", 22)
        self._client  = None

    def connect(self):
        if not HAS_PARAMIKO:
            raise ImportError("请安装 paramiko: pip install paramiko")
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(self.ip, port=self.port,
                             username=self.user, password=self.password,
                             timeout=10)

    def exec(self, cmd: str, timeout: int = 30) -> str:
        _, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors="replace").strip()
        return out

    def close(self):
        if self._client:
            self._client.close()


class _SerialConn:
    def __init__(self, cfg):
        self.port = cfg.get("serial", "/dev/ttyUSB0")
        self.baud = cfg.get("baud", 115200)
        self._s   = None
        self._buf = ""

    def connect(self):
        if not HAS_SERIAL:
            raise ImportError("请安装 pyserial: pip install pyserial")
        self._s = serial.Serial(self.port, self.baud, timeout=1)
        time.sleep(1)
        self._s.write(b"\n")

    def exec(self, cmd: str, timeout: int = 30) -> str:
        self._s.write((cmd + "\n").encode())
        deadline = time.time() + timeout
        output = ""
        while time.time() < deadline:
            line = self._s.readline().decode(errors="replace")
            output += line
            if "# " in line or "$ " in line:
                break
        return output.strip()

    def close(self):
        if self._s:
            self._s.close()
