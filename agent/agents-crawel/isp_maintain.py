#!/usr/bin/env python3
"""ISP 知识库维护脚本 — 每周刷新 Chroma 文档索引并尝试更新"""
import os, sys, hashlib, json, time
from datetime import datetime

BASE = "/home/nvidia/agi/agents-crawel"
sys.path.insert(0, BASE)

import chromadb
from chromadb.utils import embedding_functions

DB_PATH = os.path.join(BASE, "my_chroma_db")
DOCS_DIR = os.path.join(BASE, "docs")

# 文档映射
DOC_MAP = {
    "isp_pipeline_3a_tech.md":         "isp_sdk_docs",
    "chip_sdk_isp_vendors.md":         "chip_sdk_docs",
    "embedded_linux_camera_isp.md":    "embedded_linux_docs",
    "isp_video_pipeline_architecture_optimization.md": "isp_sdk_docs",
    "coding_standards_c23_misra.md":   "coding_standard_docs",
    "embedded-dev-best-practices.md":  "embedded_linux_docs",
    "embedded-linux-c-arch-framework.md": "embedded_linux_docs",
}

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] ISP知识库维护开始")
    client = chromadb.PersistentClient(path=DB_PATH)
    ef = embedding_functions.DefaultEmbeddingFunction()

    imported = 0
    skipped = 0

    for fname, coll_name in DOC_MAP.items():
        fpath = os.path.join(DOCS_DIR, fname)
        if not os.path.exists(fpath):
            skipped += 1
            continue

        mtime = os.path.getmtime(fpath)
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        coll = client.get_or_create_collection(name=coll_name, embedding_function=ef)
        doc_id = "md-" + hashlib.sha1(os.fsencode(fname)).hexdigest()
        coll.upsert(ids=[doc_id], documents=[content], metadatas=[{"source": fname}])
        imported += 1

    # 打印汇总
    for c in client.list_collections():
        col = client.get_collection(name=c.name, embedding_function=ef)
        print(f"  📂 {c.name}: {col.count()} 条")

    print(f"  导入 {imported} / 跳过 {skipped} / 总计 collections: {len(client.list_collections())}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 维护完成")

if __name__ == "__main__":
    main()
