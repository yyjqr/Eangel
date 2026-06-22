## -*- coding: UTF-8 -*-
#@author: JACK YANG
#@date:
      # 2026.04 增加
# @Email: yyjqr789@sina.com

#!/usr/bin/python3

import hashlib
import os

import chromadb
from chromadb.utils import embedding_functions

# 1. 初始化 ChromaDB (本地持久化存储)
client = chromadb.PersistentClient(path="./my_chroma_db")

# 2. 选择嵌入模型 (默认在本地运行)
# 在 Orin Nano 上，首次运行会下载模型文件
default_ef = embedding_functions.DefaultEmbeddingFunction()

# 3. 创建或获取集合
collection = client.get_or_create_collection(
    name="markdown_docs",
    embedding_function=default_ef
)


def sanitize_utf8_text(value):
    if not isinstance(value, str):
        value = str(value)
    return value.encode("utf-8", errors="replace").decode("utf-8")


def build_document_id(filename):
    digest = hashlib.sha1(os.fsencode(filename)).hexdigest()
    return f"md-{digest}"

def import_markdown_from_folder(folder_path):
    ids = []
    documents = []
    metadatas = []

    for filename in sorted(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, filename)
        if filename.endswith(".md") and os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = sanitize_utf8_text(f.read())
                safe_filename = sanitize_utf8_text(filename)
                # 这里简单处理，将整个文件作为一个 Document
                # 如果文件很大，建议先用 LangChain 的 CharacterTextSplitter 切分
                documents.append(content)
                metadatas.append({"source": safe_filename})
                ids.append(build_document_id(filename))

    if documents:
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f"成功导入 {len(documents)} 个 Markdown 文件！")

# 执行导入（假设你的 md 文件在 './docs' 文件夹）
if __name__ == "__main__":
    if not os.path.exists("./docs"):
        os.makedirs("./docs")
        print("请在 ./docs 目录下放置一些 .md 文件再运行。")
    else:
        import_markdown_from_folder("./docs")
