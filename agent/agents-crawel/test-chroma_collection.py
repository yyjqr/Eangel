python3 - <<'PY'
import chromadb
client = chromadb.PersistentClient(path="/home/nvidia/agi/agents-crawel/chroma_db")
collection = client.get_collection("milit_tech_memory")
print("count:", collection.count())
print("peek:", collection.peek())
PY
