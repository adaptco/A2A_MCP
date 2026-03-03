from qdrant_client import QdrantClient
client = QdrantClient(host="localhost", port=6333)
if hasattr(client, 'points') and client.points:
    print(f"client.points attributes: {dir(client.points)}")
try:
    import qdrant_client
    print(f"Version: {qdrant_client.__version__}")
except:
    print("Version unknown")
