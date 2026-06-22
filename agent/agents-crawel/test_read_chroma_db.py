import chromadb

client = chromadb.PersistentClient(path="./my_chroma_db") # 替换为你的数据库路径
collections = client.list_collections()
for col in collections:
    print(f"表名: {col.name}")
#collection = client.get_collection(name="your_collection_name")

    data = col.get(limit=5)

    print(data['documents']) # 打印文本内容
    print(data['metadatas']) # 打印元数据（如来源 URL、日期等）
