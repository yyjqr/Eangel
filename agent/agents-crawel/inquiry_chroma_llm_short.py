import os
import requests


def get_openai_compatible_endpoint():
    base = os.getenv("OPENAI_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    base = base.strip().strip('"').strip("'").rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def extract_dashscope_text(data):
    error = data.get("error")
    if error:
        raise RuntimeError(f"百炼调用失败: {error.get('message', error)}")

    if "choices" in data:
        return data["choices"][0]["message"]["content"]

    output = data.get("output") or {}
    choices = output.get("choices") or []
    if choices:
        return choices[0]["message"]["content"]
    if output.get("text"):
        return output["text"]

    raise RuntimeError(f"无法识别百炼返回格式: {data}")


def ask_qwen_with_context(question, context, model="qwen-plus"):
    api_key = (os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("缺少 DASHSCOPE_API_KEY")

    url = get_openai_compatible_endpoint()
    messages = [
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": f"参考上下文回答问题。\n\n上下文：\n{context}\n\n问题：{question}"},
    ]

    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
        },
        timeout=120,
    )

    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"百炼返回的不是 JSON: HTTP {resp.status_code}, body={resp.text[:500]}")

    if not resp.ok:
        message = (
            (data.get("error") or {}).get("message")
            or data.get("message")
            or resp.text
        )
        raise RuntimeError(f"百炼调用失败: HTTP {resp.status_code}, {message}")

    return extract_dashscope_text(data)
