# agents-crawel

> AI Agent 知识爬虫与检索系统 — 面向嵌入式/ISP/芯片领域的 RAG 知识库

## 项目概述

这是一个多层 AI Agent 系统，专注于：
- **知识爬取**：从多源（web、RSS、GitHub）采集嵌入式、ISP、芯片、AI 领域的技术信息
- **知识库构建**：基于 ChromaDB 的向量化存储，支持语义检索
- **Agent 推理**：结合 LLM（通义千问/DeepSeek）的 RAG 检索增强生成

## 项目结构

```
agents-crawel/
├── main-spider2.py              # 主爬虫（财经/科技新闻采集）
├── inquiry_chroma_llm.py        # ChromaDB + LLM 问答系统
├── isp_chip_agent.py            # ISP/芯片专业 Agent
├── jeston_agent_chroma_v11.py   # Jetson 嵌入式 Agent (最新版)
├── agent_hunter.py              # GitHub 仓库检索器
├── encrypt_and_verify_url.py    # URL 加密验证工具
├── docs/                        # 知识文档
│   ├── skills.md                # 科技编程技能知识库
│   ├── AI思维工具分类.md         # AI 工具分类体系
│   ├── AI科技发展图谱.md         # 技术发展趋势图
│   ├── 战略管理BLM.md            # 战略管理方法论
│   ├── linux-c-cpp容器基础.md    # Linux C/C++ 容器笔记
│   └── my_bookmarks.md          # 技术书签收藏
├── c++23进展.md                  # C++ 标准进展追踪
├── chroma_db/                   # ChromaDB 持久化向量库
└── hunter_config.json           # Hunter 编译配置
```

## 技术栈

| 组件 | 技术 |
|------|------|
| LLM | DashScope API (Qwen), DeepSeek API |
| 向量数据库 | ChromaDB (PersistentClient) |
| 爬虫 | requests, BeautifulSoup4, feedparser |
| 数据分析 | pandas, numpy, scikit-learn |
| 嵌入式 AI | NVIDIA Jetson, TensorRT, CUDA |

## 快速开始

```bash
# 安装依赖
pip install chromadb beautifulsoup4 feedparser requests scikit-learn fake-useragent

# 运行知识问答
python inquiry_chroma_llm.py

# 启动爬虫采集
python main-spider2.py
```
