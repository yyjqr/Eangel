## -*- coding: UTF-8 -*-
#@author: JACK YANG
#@date:
      # 2026.04 增加
# @Email: yyjqr789@sina.com

#!/usr/bin/python3

import argparse
import hashlib
import os
from http import HTTPStatus

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None
    embedding_functions = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "my_chroma_db")
DEFAULT_DOCS_PATH = os.path.join(BASE_DIR, "docs")
DEFAULT_COLLECTION_NAME = "markdown_docs"
DEFAULT_MODEL_NAME = "qwen3-max-2026-01-23"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MAX_CONTEXT_BYTES = 120000
DEFAULT_MAX_DOC_BYTES = 40000
DEFAULT_MAX_PROMPT_BYTES = 240000
TRUNCATION_NOTICE = "\n...[以下内容已截断]"


def list_collection_names(client):
    names = []
    for item in client.list_collections():
        names.append(getattr(item, "name", str(item)))
    return names


def get_collection(
    db_path=DEFAULT_DB_PATH,
    collection_name=DEFAULT_COLLECTION_NAME,
    create_if_missing=False,
    auto_select_single=False
):
    if chromadb is None or embedding_functions is None:
        raise ImportError("未安装 chromadb，请先执行: pip install chromadb")

    client = chromadb.PersistentClient(path=db_path)
    default_ef = embedding_functions.DefaultEmbeddingFunction()
    available_names = list_collection_names(client)

    if collection_name in available_names:
        return client.get_collection(
            name=collection_name,
            embedding_function=default_ef
        )

    if auto_select_single and not create_if_missing and len(available_names) == 1:
        auto_name = available_names[0]
        print(
            f"提示: 未找到集合 {collection_name}，"
            f"自动使用当前唯一 collection: {auto_name}"
        )
        return client.get_collection(
            name=auto_name,
            embedding_function=default_ef
        )

    if create_if_missing:
        if available_names and collection_name not in available_names:
            print(
                "提示: 当前 Chroma 库已有 collections: "
                f"{', '.join(available_names)}；将继续创建或更新 {collection_name}"
            )
        return client.get_or_create_collection(
            name=collection_name,
            embedding_function=default_ef
        )

    if not available_names:
        raise ValueError(
            f"Chroma 数据库中没有任何 collection: {db_path}。"
            "请先执行 --import-docs 导入文档，或检查 --db-path。"
        )

    raise ValueError(
        f"Collection '{collection_name}' 不存在。"
        f"当前可用 collections: {', '.join(available_names)}"
    )


def sanitize_utf8_text(value):
    if not isinstance(value, str):
        value = str(value)
    return value.encode("utf-8", errors="replace").decode("utf-8")


def utf8_len(value):
    return len(sanitize_utf8_text(value).encode("utf-8"))


def truncate_utf8_text(value, max_bytes, suffix=TRUNCATION_NOTICE):
    text = sanitize_utf8_text(value)
    if max_bytes is None or max_bytes <= 0:
        return text, False

    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text, False

    safe_suffix = sanitize_utf8_text(suffix)
    suffix_bytes = safe_suffix.encode("utf-8")
    if max_bytes <= len(suffix_bytes):
        clipped = suffix_bytes[:max_bytes].decode("utf-8", errors="ignore")
        return clipped, True

    body_limit = max_bytes - len(suffix_bytes)
    clipped = encoded[:body_limit].decode("utf-8", errors="ignore")
    return f"{clipped}{safe_suffix}", True


def build_document_id(filename):
    digest = hashlib.sha1(os.fsencode(filename)).hexdigest()
    return f"md-{digest}"


def import_markdown_from_folder(collection, folder_path):
    ids = []
    documents = []
    metadatas = []

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"请先在 {folder_path} 目录下放置 .md 文件，再重新运行导入。")
        return

    for filename in sorted(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, filename)
        if filename.endswith(".md") and os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = sanitize_utf8_text(f.read())
                safe_filename = sanitize_utf8_text(filename)
                documents.append(content)
                metadatas.append({
                    "source": safe_filename,
                    "path": sanitize_utf8_text(file_path)
                })
                ids.append(build_document_id(filename))

    if documents:
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f"成功导入或更新 {len(documents)} 个 Markdown 文件。")
    else:
        print(f"在 {folder_path} 目录下没有找到 Markdown 文件。")


def query_markdown_context(
    collection,
    query_text,
    n_results=3,
    max_context_bytes=DEFAULT_MAX_CONTEXT_BYTES,
    max_doc_bytes=DEFAULT_MAX_DOC_BYTES
):
    safe_query = sanitize_utf8_text(query_text)
    results = collection.query(
        query_texts=[safe_query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    distances = results.get("distances") or []

    if not documents or not documents[0]:
        return "", results, {
            "used_bytes": 0,
            "retrieved_results": 0,
            "included_results": 0,
            "truncated_results": 0,
            "omitted_results": 0
        }

    context_parts = []
    stats = {
        "used_bytes": 0,
        "retrieved_results": len(documents[0]),
        "included_results": 0,
        "truncated_results": 0,
        "omitted_results": 0
    }
    metadata_list = metadatas[0] if metadatas and metadatas[0] else []
    distance_list = distances[0] if distances and distances[0] else []
    for index, document in enumerate(documents[0]):
        metadata = metadata_list[index] if index < len(metadata_list) and isinstance(metadata_list[index], dict) else {}
        distance = distance_list[index] if index < len(distance_list) else None
        source = sanitize_utf8_text(metadata.get("source", f"文档{index + 1}"))
        score_text = ""
        if distance is not None:
            score_text = f" | 距离: {distance:.4f}"
        header = f"[资料{index + 1} | 来源: {source}{score_text}]\n"
        separator = "\n\n" if context_parts else ""
        remaining_bytes = None
        if max_context_bytes and max_context_bytes > 0:
            remaining_bytes = max_context_bytes - stats["used_bytes"] - utf8_len(separator)
            if remaining_bytes <= utf8_len(header):
                stats["omitted_results"] = len(documents[0]) - index
                break

        doc_text = sanitize_utf8_text(document)
        doc_truncated = False
        if max_doc_bytes and max_doc_bytes > 0:
            doc_text, doc_truncated = truncate_utf8_text(doc_text, max_doc_bytes)

        if remaining_bytes is not None:
            allowed_doc_bytes = max(remaining_bytes - utf8_len(header), 0)
            clipped_doc_text, budget_truncated = truncate_utf8_text(doc_text, allowed_doc_bytes)
        else:
            clipped_doc_text = doc_text
            budget_truncated = False

        if not clipped_doc_text:
            stats["omitted_results"] = len(documents[0]) - index
            break

        piece = f"{header}{clipped_doc_text}"
        context_parts.append(piece)
        stats["used_bytes"] += utf8_len(separator) + utf8_len(piece)
        stats["included_results"] += 1
        if doc_truncated or budget_truncated:
            stats["truncated_results"] += 1

    return "\n\n".join(context_parts), results, stats


def extract_dashscope_text(response):
    if isinstance(response, dict):
        error = response.get("error")
        if error:
            if isinstance(error, dict):
                message = error.get("message") or error.get("code") or str(error)
            else:
                message = str(error)
            raise RuntimeError(f"百炼调用失败: {message}")

        choices = response.get("choices") or []
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content

        output = response.get("output") or {}
        if isinstance(output, dict):
            if output.get("text"):
                return output["text"]
            choices = output.get("choices") or []
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content")
                if isinstance(content, str):
                    return content

    status_code = getattr(response, "status_code", None)
    if status_code not in (None, HTTPStatus.OK):
        message = getattr(response, "message", None) or getattr(response, "code", None) or str(response)
        raise RuntimeError(f"百炼调用失败: {message}")

    output = getattr(response, "output", None)
    if output is not None:
        text = getattr(output, "text", None)
        if text:
            return text
        if isinstance(output, dict):
            if output.get("text"):
                return output["text"]
            choices = output.get("choices") or []
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content")
                if isinstance(content, str):
                    return content

    if isinstance(response, dict):
        output = response.get("output", {})
        if output.get("text"):
            return output["text"]

    raise RuntimeError(f"无法从百炼响应中提取文本: {response}")


def build_chat_completions_url(base_url=None):
    resolved_base_url = base_url or os.getenv("OPENAI_API_BASE") or os.getenv("DASHSCOPE_BASE_URL") or DEFAULT_BASE_URL
    resolved_base_url = sanitize_utf8_text(resolved_base_url).strip().strip('"').strip("'").rstrip("/")
    if resolved_base_url.endswith("/chat/completions"):
        return resolved_base_url
    return f"{resolved_base_url}/chat/completions"


def build_rag_prompt(query_text, context):
    return f"""你是一个基于检索资料回答问题的助手。
请严格依据提供的参考资料回答：
1. 先给出简洁结论。
2. 再分点总结依据。
3. 如果参考资料不足以回答，请明确说明“参考资料不足”。

参考资料：
{context}

用户问题：
{sanitize_utf8_text(query_text)}
"""


def ask_qwen_with_context(
    query_text,
    context,
    model_name=DEFAULT_MODEL_NAME,
    api_key=None,
    max_prompt_bytes=DEFAULT_MAX_PROMPT_BYTES,
    base_url=None,
    timeout=120
):
    try:
        import requests
    except ImportError as exc:
        raise ImportError("未安装 requests，请先执行: pip install requests") from exc

    api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("请先设置 DASHSCOPE_API_KEY / OPENAI_API_KEY 环境变量，或通过 --api-key 传入。")

    prompt = build_rag_prompt(query_text, context)
    prompt_bytes = utf8_len(prompt)
    if max_prompt_bytes and prompt_bytes > max_prompt_bytes:
        raise RuntimeError(
            "百炼请求未发送：prompt 过长，"
            f"当前约 {prompt_bytes} bytes，限制为 {max_prompt_bytes} bytes。"
            "请降低 --n-results，或调小 --max-context-bytes / --max-doc-bytes。"
        )

    url = build_chat_completions_url(base_url)
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        },
        timeout=timeout,
    )

    try:
        response_data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"百炼返回的不是 JSON: HTTP {response.status_code}, body={response.text[:500]}"
        ) from exc

    if not response.ok:
        error = response_data.get("error", {}) if isinstance(response_data, dict) else {}
        message = error.get("message") or error.get("code")
        if not message and isinstance(response_data, dict):
            message = response_data.get("message")
        if not message:
            message = response.text[:500]
        raise RuntimeError(f"百炼调用失败: HTTP {response.status_code}, {message}")

    return extract_dashscope_text(response_data)


def run_rag_answer(
    collection,
    query_text,
    n_results=3,
    model_name=DEFAULT_MODEL_NAME,
    api_key=None,
    base_url=None,
    show_context=False,
    max_context_bytes=DEFAULT_MAX_CONTEXT_BYTES,
    max_doc_bytes=DEFAULT_MAX_DOC_BYTES,
    max_prompt_bytes=DEFAULT_MAX_PROMPT_BYTES
):
    if collection.count() == 0:
        raise ValueError("当前 Chroma 集合为空，请先使用 --import-docs 导入 Markdown 文档。")

    context, _, stats = query_markdown_context(
        collection,
        query_text,
        n_results=n_results,
        max_context_bytes=max_context_bytes,
        max_doc_bytes=max_doc_bytes
    )
    if not context:
        print("没有检索到相关资料。")
        return

    if stats["truncated_results"] or stats["omitted_results"]:
        print(
            "提示: 检索上下文已按字节数裁剪，"
            f"最终发送 {stats['used_bytes']} bytes，"
            f"纳入 {stats['included_results']}/{stats['retrieved_results']} 条结果，"
            f"截断 {stats['truncated_results']} 条，省略 {stats['omitted_results']} 条。"
        )

    if show_context:
        print("===== 检索结果 =====")
        print(context)
        print()

    answer = ask_qwen_with_context(
        query_text=query_text,
        context=context,
        model_name=model_name,
        api_key=api_key,
        max_prompt_bytes=max_prompt_bytes,
        base_url=base_url
    )
    print("===== Qwen 总结结果 =====")
    print(answer)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Markdown -> Chroma -> 百炼 Qwen 的最小 RAG 示例"
    )
    parser.add_argument(
        "--import-docs",
        action="store_true",
        help="把 docs 目录下的 Markdown 文档导入到 Chroma"
    )
    parser.add_argument(
        "--question",
        help="用户问题。传入后会先从 Chroma 检索，再调用百炼 Qwen 生成答案"
    )
    parser.add_argument(
        "--docs",
        default=DEFAULT_DOCS_PATH,
        help=f"Markdown 文档目录，默认: {DEFAULT_DOCS_PATH}"
    )
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_PATH,
        help=f"Chroma 持久化目录，默认: {DEFAULT_DB_PATH}"
    )
    parser.add_argument(
        "--collection-name",
        default=DEFAULT_COLLECTION_NAME,
        help=f"Chroma 集合名称，默认: {DEFAULT_COLLECTION_NAME}"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_NAME,
        help=f"百炼模型名，默认: {DEFAULT_MODEL_NAME}"
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_API_BASE") or os.getenv("DASHSCOPE_BASE_URL") or DEFAULT_BASE_URL,
        help="OpenAI 兼容接口 base_url，默认优先读取 OPENAI_API_BASE / DASHSCOPE_BASE_URL"
    )
    parser.add_argument(
        "--n-results",
        type=int,
        default=3,
        help="检索返回的文档条数，默认: 3"
    )
    parser.add_argument(
        "--max-context-bytes",
        type=int,
        default=DEFAULT_MAX_CONTEXT_BYTES,
        help=f"发送给百炼的总上下文字节上限，默认: {DEFAULT_MAX_CONTEXT_BYTES}"
    )
    parser.add_argument(
        "--max-doc-bytes",
        type=int,
        default=DEFAULT_MAX_DOC_BYTES,
        help=f"单条检索结果纳入上下文的字节上限，默认: {DEFAULT_MAX_DOC_BYTES}"
    )
    parser.add_argument(
        "--max-prompt-bytes",
        type=int,
        default=DEFAULT_MAX_PROMPT_BYTES,
        help=f"发送给百炼的 prompt 字节上限，默认: {DEFAULT_MAX_PROMPT_BYTES}"
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("DASHSCOPE_API_KEY"),
        help="百炼 API Key，默认读取环境变量 DASHSCOPE_API_KEY"
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="先打印检索到的上下文，再打印 Qwen 生成结果"
    )
    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    if not args.import_docs and not args.question:
        parser.print_help()
    else:
        collection = get_collection(
            db_path=args.db_path,
            collection_name=args.collection_name,
            create_if_missing=args.import_docs,
            auto_select_single=not args.import_docs
        )

        if args.import_docs:
            import_markdown_from_folder(collection, args.docs)

        if args.question:
            run_rag_answer(
                collection=collection,
                query_text=args.question,
                n_results=args.n_results,
                model_name=args.model,
                api_key=args.api_key,
                base_url=args.base_url,
                show_context=args.show_context,
                max_context_bytes=args.max_context_bytes,
                max_doc_bytes=args.max_doc_bytes,
                max_prompt_bytes=args.max_prompt_bytes
            )
