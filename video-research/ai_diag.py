"""
AI 智能诊断模块
将 FAIL 用例的结构化结果 + dmesg 日志交给 LLM（Claude / OpenAI / 本地 Hermes）
自动生成：故障根因分析 + 修复建议 + 测试代码改进方案
"""

import json
import os
import sys
import datetime

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


# ═══════════════════════════════════════════════════════════
# 对外入口
# ═══════════════════════════════════════════════════════════

def run_ai_diagnosis(ai_cfg: dict, fail_results: list, report_dir: str,
                     dmesg_path: str = None):
    """
    ai_cfg: config.json["ai_diag"]
    fail_results: 失败用例的结果列表
    dmesg_path: 可选，板端 dmesg 日志文件路径
    """
    if not fail_results:
        return

    console.print("\n[bold magenta]🤖 启动 AI 故障诊断...[/bold magenta]")

    dmesg_text = ""
    if dmesg_path and os.path.exists(dmesg_path):
        with open(dmesg_path, encoding="utf-8", errors="replace") as f:
            dmesg_text = f.read()[-4000:]   # 只取末尾 4000 字符

    prompt = _build_prompt(fail_results, dmesg_text)

    provider = ai_cfg.get("provider", "claude")
    try:
        if provider == "claude":
            diag_text = _call_claude(ai_cfg, prompt)
        elif provider == "openai":
            diag_text = _call_openai(ai_cfg, prompt)
        elif provider == "hermes_local":
            diag_text = _call_hermes_local(ai_cfg, prompt)
        else:
            console.print(f"[red]未知 AI provider: {provider}[/red]")
            return
    except Exception as e:
        console.print(f"[red]AI 调用失败: {e}[/red]")
        return

    # 渲染到终端
    console.print(Panel(
        Markdown(diag_text),
        title="[bold magenta]🤖 AI 故障诊断报告",
        border_style="magenta",
    ))

    # 保存到文件
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    diag_path = os.path.join(report_dir, f"ai_diag_{ts}.md")
    with open(diag_path, "w", encoding="utf-8") as f:
        f.write(f"# AI 故障诊断报告\n\n生成时间: {ts}\n\n")
        f.write(diag_text)
    console.print(f"[bold magenta]📝 诊断报告已保存: {diag_path}[/bold magenta]")


# ═══════════════════════════════════════════════════════════
# Prompt 构建
# ═══════════════════════════════════════════════════════════

def _build_prompt(fail_results: list, dmesg_text: str) -> str:
    fail_json = json.dumps(fail_results, ensure_ascii=False, indent=2)
    dmesg_section = f"\n\n## 板端 dmesg 日志（末尾片段）\n```\n{dmesg_text}\n```" if dmesg_text else ""

    return f"""你是一位嵌入式 Linux SoC 多媒体（ISP/VENC/AUDIO/AI）测试专家。
以下是我的 SoC 音视频自动化 HIL 测试平台生成的 **FAIL 用例结果**，
请完成以下分析：

1. **根因分析**：每个 FAIL 用例的可能硬件/驱动/SDK 根因（参考 reason 字段与 dmesg）
2. **鉴别表**：区分是 MIPI 丢包 / AXI 带宽溢出 / 内存泄漏 / 驱动 Bug / 测试脚本误报
3. **修复建议**：针对每个 FAIL 给出具体的调试命令或驱动参数修改方案
4. **测试优化**：指出测试用例阈值是否需要调整（如 bad_pixel_ratio / snr_min_db）

## FAIL 用例结果
```json
{fail_json}
```
{dmesg_section}

请用 Markdown 格式输出，分章节清晰展示。"""


# ═══════════════════════════════════════════════════════════
# LLM 调用适配器
# ═══════════════════════════════════════════════════════════

def _call_claude(ai_cfg: dict, prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise ImportError("请安装: pip install anthropic")

    api_key = os.environ.get(ai_cfg.get("api_key_env", "ANTHROPIC_API_KEY"), "")
    if not api_key:
        raise ValueError(f"环境变量 {ai_cfg.get('api_key_env')} 未设置")

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=ai_cfg.get("model", "claude-3-5-sonnet-20241022"),
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _call_openai(ai_cfg: dict, prompt: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("请安装: pip install openai")

    api_key = os.environ.get(ai_cfg.get("api_key_env", "OPENAI_API_KEY"), "")
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=ai_cfg.get("model", "gpt-4o"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
    )
    return resp.choices[0].message.content


def _call_hermes_local(ai_cfg: dict, prompt: str) -> str:
    """
    调用本地 Hermes/Ollama 等兼容 OpenAI 格式的本地模型
    需在 ai_cfg 中设置 base_url，如 http://localhost:11434/v1
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("请安装: pip install openai")

    base_url = ai_cfg.get("base_url", "http://localhost:11434/v1")
    client = OpenAI(api_key="local", base_url=base_url)
    resp = client.chat.completions.create(
        model=ai_cfg.get("model", "hermes3"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
    )
    return resp.choices[0].message.content


# ═══════════════════════════════════════════════════════════
# 独立运行：直接对已有的 test_summary_latest.json 进行诊断
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="对已有 JSON 报告进行 AI 诊断")
    p.add_argument("--report",  default="./reports/test_summary_latest.json")
    p.add_argument("--dmesg",   default="")
    p.add_argument("--config",  default="config.json")
    p.add_argument("--provider",default="")
    args = p.parse_args()

    cfg_path = os.path.join(os.path.dirname(__file__), args.config)
    with open(cfg_path) as f:
        cfg = json.load(f)

    with open(args.report, encoding="utf-8") as f:
        summary = json.load(f)

    ai_cfg = cfg.get("ai_diag", {"enabled": True, "provider": "claude"})
    if args.provider:
        ai_cfg["provider"] = args.provider
    ai_cfg["enabled"] = True

    fails = [r for r in summary.get("test_results", []) if r["status"] == "FAIL"]
    if not fails:
        console.print("[green]没有 FAIL 用例，无需诊断[/green]")
        sys.exit(0)

    run_ai_diagnosis(ai_cfg, fails, os.path.dirname(args.report),
                     dmesg_path=args.dmesg or None)
