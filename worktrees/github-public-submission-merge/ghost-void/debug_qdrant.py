from qdrant_client import QdrantClient
print(f"QdrantClient imported from {QdrantClient}")
client = QdrantClient(host="localhost", port=6333)
print(f"Attributes: {dir(client)}")
try:
    client.search
    print("search method exists")
except AttributeError:
    print("search method MISSING")
