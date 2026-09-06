"""
SoC 音视频自动化测试主调度器
可视化：Rich 实时进度 + 分组表格 + 系统监控侧栏
用法：
  python test_runner.py                      # 跑全部 enabled 用例
  python test_runner.py --tags smoke         # 只跑 smoke 标签
  python test_runner.py --group VI,VENC      # 只跑指定分组
  python test_runner.py --dut DUT-A          # 指定 DUT
  python test_runner.py --dry-run            # 仅列出用例不执行
  python test_runner.py --config my.json     # 指定配置文件
"""

import argparse
import json
import os
import sys
import time
import threading
import datetime
from typing import Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, TextColumn,
    BarColumn, TaskProgressColumn, TimeElapsedColumn, MofNCompleteColumn,
)
from rich.table import Table
from rich.text import Text
from rich import box

# ── 本项目模块 ────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from dut_client import DUTClient
from sample_tests.test_executor import TestExecutor

console = Console()

# ═══════════════════════════════════════════════════════════
# 配置加载
# ═══════════════════════════════════════════════════════════

def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    # 将 {bin} 占位符替换为板端 sample_bin_dir
    return cfg


def resolve_sdk_cmd(cmd: str, dut_cfg: dict) -> str:
    bin_dir = dut_cfg.get("sample_bin_dir", "/userdata/sample")
    return cmd.replace("{bin}", bin_dir)


def filter_cases(cases: list, tags: list, groups: list) -> list:
    result = [c for c in cases if c.get("enabled", True)]
    if tags:
        result = [c for c in result if any(t in c.get("tags", []) for t in tags)]
    if groups:
        result = [c for c in result if c.get("group", "") in groups]
    return result


# ═══════════════════════════════════════════════════════════
# 系统资源监控（后台轮询）
# ═══════════════════════════════════════════════════════════

class SysMonitor:
    def __init__(self, dut: DUTClient, interval: float = 5.0):
        self.dut      = dut
        self.interval = interval
        self.cpu      = -1.0
        self.mem_mb   = -1.0
        self.temp_c   = -1.0
        self._stop    = threading.Event()
        self._thread  = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.cpu    = self.dut.get_cpu_usage()
                self.mem_mb = self.dut.get_mem_free_mb()
                self.temp_c = self.dut.get_cpu_temp()
            except Exception:
                pass
            self._stop.wait(self.interval)

    def render_panel(self) -> Panel:
        from config import THRESHOLDS
        def _color(val, warn, crit, invert=False):
            """invert=True 时低值报警（如内存空闲）"""
            if val < 0:
                return "dim"
            if invert:
                return "green" if val > warn else ("yellow" if val > crit else "red")
            return "green" if val < warn else ("yellow" if val < crit else "red")

        t = THRESHOLDS["system"]
        lines = [
            f"[bold]DUT:[/bold] {self.dut.name}  [{self.dut.cfg.get('chip','')}]",
            "",
            f"CPU  [{_color(self.cpu, 70, t['cpu_max_pct'])}]{self.cpu:>5.1f}%[/]",
            f"Mem  [{_color(self.mem_mb, t['mem_free_min_mb']*3, t['mem_free_min_mb'], invert=True)}]{self.mem_mb:>5.1f} MB free[/]",
            f"Temp [{_color(self.temp_c, 70, t['temp_max_celsius'])}]{self.temp_c:>5.1f} °C[/]",
        ]
        return Panel("\n".join(lines), title="[cyan]板端状态", border_style="cyan", width=28)


# ═══════════════════════════════════════════════════════════
# 结果渲染
# ═══════════════════════════════════════════════════════════

STATUS_ICON = {
    "PASS"   : "[bold green]✓ PASS[/bold green]",
    "FAIL"   : "[bold red]✗ FAIL[/bold red]",
    "SKIP"   : "[dim]— SKIP[/dim]",
    "RUNNING": "[yellow]⟳ ...[/yellow]",
    "PENDING": "[dim]  ···[/dim]",
    "ERROR"  : "[bold magenta]⚠ ERR[/bold magenta]",
}

GROUP_COLORS = {
    "VI"         : "cyan",
    "VENC"       : "blue",
    "VIDEO"      : "bright_blue",
    "AUDIO"      : "magenta",
    "MultiCAM"   : "bright_cyan",
    "AI"         : "bright_magenta",
    "SVP"        : "yellow",
    "Robustness" : "red",
}

def build_result_table(results: list) -> Table:
    table = Table(
        title="[bold]SoC 自动化测试结果汇总",
        box=box.ROUNDED, show_lines=True,
        title_style="bold white on dark_blue",
    )
    table.add_column("ID",     style="cyan",    no_wrap=True, width=14)
    table.add_column("分组",   style="bold",    width=10)
    table.add_column("测试项", width=28)
    table.add_column("结果",   justify="center", width=10)
    table.add_column("关键指标", style="green",  width=30)
    table.add_column("失败原因", style="red",    width=30)

    for r in results:
        grp_color = GROUP_COLORS.get(r.get("group", ""), "white")
        metrics_str = _fmt_metrics(r.get("metrics", {}))
        table.add_row(
            r["id"],
            f"[{grp_color}]{r.get('group','')}[/]",
            r["name"],
            STATUS_ICON.get(r["status"], r["status"]),
            metrics_str,
            r.get("reason", ""),
        )
    return table


def build_summary_panel(results: list, elapsed: float) -> Panel:
    total  = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    skipped= sum(1 for r in results if r["status"] == "SKIP")

    rate = passed / max(total - skipped, 1) * 100
    color = "green" if rate == 100 else ("yellow" if rate >= 80 else "red")

    lines = [
        f"总用例: [bold]{total}[/bold]   "
        f"[green]✓ {passed}[/green]  "
        f"[red]✗ {failed}[/red]  "
        f"[magenta]⚠ {errors}[/magenta]  "
        f"[dim]— {skipped}[/dim]",
        f"通过率: [{color}][bold]{rate:.1f}%[/bold][/]   "
        f"耗时: [white]{elapsed:.1f}s[/white]",
    ]
    return Panel("\n".join(lines), title="[bold]汇总", border_style=color)


def _fmt_metrics(m: dict) -> str:
    if not m:
        return ""
    parts = []
    for k, v in list(m.items())[:3]:   # 最多显示 3 个指标
        parts.append(f"{k}={v}")
    return "  ".join(parts)


# ═══════════════════════════════════════════════════════════
# 主运行逻辑
# ═══════════════════════════════════════════════════════════

def run(cfg: dict, cases: list, dut_cfg: dict, dry_run: bool = False):
    server_ip  = cfg["server"]["ip"]
    base_port  = cfg["server"].get("base_port", 9000)
    report_dir = cfg.get("report_dir", "./reports")
    os.makedirs(report_dir, exist_ok=True)
    os.makedirs(os.path.join(report_dir, "logs"),  exist_ok=True)
    os.makedirs(os.path.join(report_dir, "media"), exist_ok=True)

    # 注入全局 thresholds 到 config 模块
    import config as _cfg_mod
    _cfg_mod.THRESHOLDS = cfg["thresholds"]
    _cfg_mod.REPORT_DIR = report_dir
    _cfg_mod.LOG_DIR    = os.path.join(report_dir, "logs")
    _cfg_mod.MEDIA_DIR  = os.path.join(report_dir, "media")
    _cfg_mod.SERVER_IP  = server_ip
    _cfg_mod.AI_DIAG    = cfg.get("ai_diag", {"enabled": False})

    # 初始化结果列表（先全部 PENDING）
    results = [
        {"id": c["id"], "group": c.get("group",""), "name": c["name"],
         "status": "PENDING", "metrics": {}, "reason": ""}
        for c in cases
    ]

    if dry_run:
        console.print(build_result_table(
            [dict(r, status="SKIP") for r in results]
        ))
        console.print(f"[dim]Dry-run: {len(cases)} 个用例，未执行[/dim]")
        return

    # ── 连接 DUT ──────────────────────────────────────────
    dut = DUTClient(dut_cfg)
    console.print(f"\n[bold cyan]🔌 连接板端 {dut_cfg['name']} ({dut_cfg['ip']})...[/bold cyan]")
    try:
        dut.connect()
        console.print(f"[bold green]✓ 连接成功  芯片: {dut_cfg.get('chip','')}  内存: {dut_cfg.get('memory_mb','')}MB[/bold green]\n")
    except Exception as e:
        console.print(f"[bold red]✗ 连接失败: {e}[/bold red]")
        return

    monitor = SysMonitor(dut)
    monitor.start()

    executor = TestExecutor(dut, server_ip, base_port)

    # ── Rich 布局：左进度 + 右系统状态 ───────────────────
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}", width=36),
        BarColumn(bar_width=24),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )
    total_task = progress.add_task("[yellow]总体进度", total=len(cases))

    start_time = time.time()

    with Live(console=console, refresh_per_second=4, vertical_overflow="visible") as live:
        def _render():
            done = [r for r in results if r["status"] not in ("PENDING", "RUNNING")]
            layout = Layout()
            layout.split_row(
                Layout(Panel(progress, title="[bold]执行进度", border_style="yellow"), ratio=5),
                Layout(monitor.render_panel(), ratio=2),
            )
            return layout

        live.update(_render())

        for idx, tc in enumerate(cases):
            # 替换 {bin} 占位符
            tc = dict(tc)
            tc["sdk_cmd"] = resolve_sdk_cmd(tc.get("sdk_cmd", ""), dut_cfg)

            results[idx]["status"] = "RUNNING"
            progress.update(
                total_task,
                description=f"[cyan]{tc['id']}[/cyan] {tc['name'][:28]}",
            )
            live.update(_render())

            t0 = time.time()
            result = executor.run(tc)
            elapsed_tc = time.time() - t0

            status = "PASS" if result.get("pass") is True else \
                     ("SKIP" if result.get("pass") is None else "FAIL")
            results[idx].update({
                "status" : status,
                "metrics": result.get("metrics", {}),
                "reason" : result.get("reason", ""),
                "elapsed": round(elapsed_tc, 1),
            })

            progress.advance(total_task)
            live.update(_render())

            # 实时打印该条结果（滚动区）
            icon = STATUS_ICON.get(status, status)
            m_str = _fmt_metrics(result.get("metrics", {}))
            console.print(
                f"  {icon}  [cyan]{tc['id']:14}[/cyan]"
                f"  [{GROUP_COLORS.get(tc.get('group',''),'white')}]{tc.get('group',''):10}[/]"
                f"  {tc['name'][:28]:28}"
                f"  [dim]{elapsed_tc:.1f}s[/dim]"
                + (f"  [green]{m_str}[/green]" if m_str else "")
                + (f"\n    [red]↳ {result.get('reason','')}[/red]" if status == "FAIL" else "")
            )
            live.update(_render())

    # ── 最终汇总 ──────────────────────────────────────────
    total_elapsed = time.time() - start_time
    console.print()
    console.print(build_result_table(results))
    console.print(build_summary_panel(results, total_elapsed))

    monitor.stop()
    dut.close()

    # ── 保存报告 ──────────────────────────────────────────
    _save_reports(cfg, results, total_elapsed, report_dir)

    # ── AI 诊断（可选）───────────────────────────────────
    fail_cases = [r for r in results if r["status"] == "FAIL"]
    if cfg.get("ai_diag", {}).get("enabled") and fail_cases:
        from ai_diag import run_ai_diagnosis
        run_ai_diagnosis(cfg["ai_diag"], fail_cases, report_dir)


# ═══════════════════════════════════════════════════════════
# 报告持久化
# ═══════════════════════════════════════════════════════════

def _save_reports(cfg: dict, results: list, elapsed: float, report_dir: str):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON 报告（供 Agent 分析）
    summary = {
        "timestamp"    : ts,
        "elapsed_s"    : round(elapsed, 1),
        "total"        : len(results),
        "passed"       : sum(1 for r in results if r["status"] == "PASS"),
        "failed"       : sum(1 for r in results if r["status"] == "FAIL"),
        "skipped"      : sum(1 for r in results if r["status"] == "SKIP"),
        "dut"          : cfg["duts"][0].get("name", ""),
        "chip"         : cfg["duts"][0].get("chip", ""),
        "test_results" : results,
    }
    json_path = os.path.join(report_dir, f"test_summary_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # 同时覆盖写一份 latest
    latest = os.path.join(report_dir, "test_summary_latest.json")
    with open(latest, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # HTML 报告（简版）
    html_path = os.path.join(report_dir, f"report_{ts}.html")
    _write_html_report(summary, html_path)

    console.print(f"\n[bold green]📄 JSON 报告: [link]{json_path}[/link][/bold green]")
    console.print(f"[bold green]🌐 HTML 报告: [link]{html_path}[/link][/bold green]")


def _write_html_report(summary: dict, path: str):
    group_colors = {
        "VI":"#00bcd4","VENC":"#3f51b5","VIDEO":"#2196f3",
        "AUDIO":"#9c27b0","MultiCAM":"#00acc1","AI":"#e91e63",
        "SVP":"#ff9800","Robustness":"#f44336",
    }
    rows = ""
    for r in summary["test_results"]:
        bg = "#1b5e20" if r["status"]=="PASS" else ("#b71c1c" if r["status"]=="FAIL" else "#333")
        icon = "✓" if r["status"]=="PASS" else ("✗" if r["status"]=="FAIL" else "—")
        gc = group_colors.get(r.get("group",""), "#888")
        m_str = _fmt_metrics(r.get("metrics", {}))
        rows += f"""
        <tr>
          <td style='color:#4fc3f7'>{r['id']}</td>
          <td><span style='background:{gc};padding:2px 6px;border-radius:3px;font-size:12px'>{r.get('group','')}</span></td>
          <td>{r['name']}</td>
          <td style='background:{bg};text-align:center;font-weight:bold'>{icon} {r['status']}</td>
          <td style='color:#a5d6a7;font-size:12px'>{m_str}</td>
          <td style='color:#ef9a9a;font-size:12px'>{r.get('reason','')}</td>
          <td style='color:#888'>{r.get('elapsed','')}</td>
        </tr>"""

    ts_fmt = summary['timestamp']
    rate = summary['passed'] / max(summary['total'] - summary['skipped'], 1) * 100
    rate_color = "#4caf50" if rate == 100 else ("#ffeb3b" if rate >= 80 else "#f44336")

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><title>SoC 测试报告 {ts_fmt}</title>
<style>
  body{{background:#121212;color:#e0e0e0;font-family:'Segoe UI',monospace;margin:24px}}
  h1{{color:#80cbc4}} h2{{color:#b0bec5}}
  .summary{{display:flex;gap:32px;margin:16px 0;padding:16px;background:#1e1e1e;border-radius:8px}}
  .stat{{text-align:center}} .stat .val{{font-size:2em;font-weight:bold}}
  table{{width:100%;border-collapse:collapse;margin-top:16px}}
  th{{background:#263238;padding:10px 8px;text-align:left;color:#80deea;font-size:13px}}
  td{{padding:8px;border-bottom:1px solid #263238;font-size:13px}}
  tr:hover td{{background:#1a2a30}}
</style></head>
<body>
<h1>📊 SoC 自动化测试报告</h1>
<div class="summary">
  <div class="stat"><div class="val">{summary['total']}</div><div>总用例</div></div>
  <div class="stat"><div class="val" style="color:#4caf50">{summary['passed']}</div><div>通过</div></div>
  <div class="stat"><div class="val" style="color:#f44336">{summary['failed']}</div><div>失败</div></div>
  <div class="stat"><div class="val" style="color:{rate_color}">{rate:.1f}%</div><div>通过率</div></div>
  <div class="stat"><div class="val">{summary['elapsed_s']}s</div><div>耗时</div></div>
  <div class="stat"><div style="font-size:0.9em;color:#80cbc4">{summary['chip']}</div><div>{summary['dut']}</div></div>
</div>
<table>
  <tr><th>用例 ID</th><th>分组</th><th>测试项</th><th>结果</th><th>关键指标</th><th>失败原因</th><th>耗时</th></tr>
  {rows}
</table>
<p style="color:#555;font-size:12px;margin-top:32px">生成时间: {ts_fmt}</p>
</body></html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


# ═══════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="SoC 音视频自动化测试调度器")
    parser.add_argument("--config",  default="config.json", help="配置文件路径")
    parser.add_argument("--tags",    default="",            help="只运行包含这些 tag 的用例，逗号分隔")
    parser.add_argument("--group",   default="",            help="只运行指定分组，逗号分隔 (VI,VENC,...)")
    parser.add_argument("--dut",     default="",            help="指定 DUT name（默认第一个）")
    parser.add_argument("--dry-run", action="store_true",   help="列出用例但不执行")
    args = parser.parse_args()

    cfg_path = os.path.join(os.path.dirname(__file__), args.config)
    if not os.path.exists(cfg_path):
        console.print(f"[red]配置文件不存在: {cfg_path}[/red]")
        sys.exit(1)

    cfg = load_config(cfg_path)

    # 选择 DUT
    dut_cfg = cfg["duts"][0]
    if args.dut:
        for d in cfg["duts"]:
            if d["name"] == args.dut:
                dut_cfg = d
                break

    # 过滤用例
    tags   = [t.strip() for t in args.tags.split(",")  if t.strip()]
    groups = [g.strip() for g in args.group.split(",") if g.strip()]
    cases  = filter_cases(cfg.get("test_cases", []), tags, groups)

    if not cases:
        console.print("[yellow]没有匹配的用例，请检查 --tags / --group 参数[/yellow]")
        sys.exit(0)

    console.print(f"\n[bold cyan]🚀 SoC 音视频自动化 HIL 测试平台[/bold cyan]  "
                  f"[dim]v1.0  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}[/dim]")
    console.print(f"[dim]配置: {cfg_path}  |  用例: {len(cases)}  |  DUT: {dut_cfg['name']}[/dim]\n")

    run(cfg, cases, dut_cfg, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
