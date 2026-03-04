from qdrant_client import QdrantClient
client = QdrantClient(host="localhost", port=6333)
print(f"Full Dir: {dir(client)}")
