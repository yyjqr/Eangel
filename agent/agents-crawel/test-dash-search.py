import os
import requests


def build_chat_completions_url():
    base_url = (
        os.getenv("OPENAI_API_BASE")
        or os.getenv("DASHSCOPE_BASE_URL")
        or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    base_url = base_url.strip().strip('"').strip("'").rstrip("/")

    if base_url.endswith("/chat/completions"):
        return base_url
    return f"{base_url}/chat/completions"


def extract_dashscope_text(data):
    if not isinstance(data, dict):
        raise RuntimeError(f"百炼返回格式错误: {type(data).__name__}")

    error = data.get("error")
    if error:
        if isinstance(error, dict):
            message = error.get("message") or str(error)
        else:
            message = str(error)
        raise RuntimeError(f"百炼调用失败: {message}")

    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        raise RuntimeError(f"百炼返回 content 格式异常: {content!r}")

    output = data.get("output")
    if isinstance(output, dict):
        output_choices = output.get("choices")
        if isinstance(output_choices, list) and output_choices:
            message = output_choices[0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, str):
                return content

        text = output.get("text")
        if isinstance(text, str):
            return text

    raise RuntimeError(f"无法识别百炼返回格式: {data}")


def ask_qwen_with_context(question, context, model="qwen-plus", timeout=120):
    api_key = (os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("缺少 DASHSCOPE_API_KEY 或 OPENAI_API_KEY")

    url = build_chat_completions_url()

    messages = [
        {
            "role": "system",
            "content": "你是一个有帮助的助手，请严格基于提供的上下文回答问题。"
        },
        {
            "role": "user",
            "content": f"上下文：\n{context}\n\n问题：{question}"
        }
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
        timeout=timeout,
    )

    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"百炼返回的不是 JSON: HTTP {resp.status_code}, body={resp.text[:500]}")

    if not resp.ok:
        error = data.get("error", {})
        message = error.get("message") or data.get("message") or resp.text
        raise RuntimeError(f"百炼调用失败: HTTP {resp.status_code}, {message}")

    return extract_dashscope_text(data)


if __name__ == "__main__":
    #question = "最新软件，c++进展"
    question = "最新移动机器人，人型机器人，欧美和中国的发展进展"
    context = "这里替换成你检索出来的上下文"
    answer = ask_qwen_with_context(question, context)
    print(answer)
