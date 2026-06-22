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


def get_collection(db_path=DEFAULT_DB_PATH, collection_name=DEFAULT_COLLECTION_NAME):
    if chromadb is None or embedding_functions is None:
        raise ImportError("未安装 chromadb，请先执行: pip install chromadb")

    client = chromadb.PersistentClient(path=db_path)
    default_ef = embedding_functions.DefaultEmbeddingFunction()
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=default_ef
    )


def sanitize_utf8_text(value):
    if not isinstance(value, str):
        value = str(value)
    return value.encode("utf-8", errors="replace").decode("utf-8")


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


def query_markdown_context(collection, query_text, n_results=3):
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
        return "", results

    context_parts = []
    metadata_list = metadatas[0] if metadatas and metadatas[0] else []
    distance_list = distances[0] if distances and distances[0] else []
    for index, document in enumerate(documents[0]):
        metadata = metadata_list[index] if index < len(metadata_list) else {}
        distance = distance_list[index] if index < len(distance_list) else None
        source = metadata.get("source", f"文档{index + 1}")
        score_text = ""
        if distance is not None:
            score_text = f" | 距离: {distance:.4f}"
        context_parts.append(
            f"[资料{index + 1} | 来源: {source}{score_text}]\n{sanitize_utf8_text(document)}"
        )

    return "\n\n".join(context_parts), results


def extract_dashscope_text(response):
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


def ask_qwen_with_context(query_text, context, model_name=DEFAULT_MODEL_NAME, api_key=None):
    try:
        import dashscope
    except ImportError as exc:
        raise ImportError("未安装 dashscope，请先执行: pip install dashscope") from exc

    api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("请先设置 DASHSCOPE_API_KEY 环境变量，或通过 --api-key 传入。")

    prompt = f"""你是一个基于检索资料回答问题的助手。
请严格依据提供的参考资料回答：
1. 先给出简洁结论。
2. 再分点总结依据。
3. 如果参考资料不足以回答，请明确说明“参考资料不足”。

参考资料：
{context}

用户问题：
{sanitize_utf8_text(query_text)}
"""

    response = dashscope.Generation.call(
        model=model_name,
        prompt=prompt,
        api_key=api_key
    )
    return extract_dashscope_text(response)


def run_rag_answer(collection, query_text, n_results=3, model_name=DEFAULT_MODEL_NAME, api_key=None, show_context=False):
    if collection.count() == 0:
        raise ValueError("当前 Chroma 集合为空，请先使用 --import-docs 导入 Markdown 文档。")

    context, _ = query_markdown_context(collection, query_text, n_results=n_results)
    if not context:
        print("没有检索到相关资料。")
        return

    if show_context:
        print("===== 检索结果 =====")
        print(context)
        print()

    answer = ask_qwen_with_context(
        query_text=query_text,
        context=context,
        model_name=model_name,
        api_key=api_key
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
        "--n-results",
        type=int,
        default=3,
        help="检索返回的文档条数，默认: 3"
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
            collection_name=args.collection_name
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
                show_context=args.show_context
            )
