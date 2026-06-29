import os
import time
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME", "samas-index")

pc = Pinecone(api_key=api_key)

if index_name in pc.list_indexes().names():
    print(f"Deleting existing index '{index_name}'...")
    pc.delete_index(index_name)
    time.sleep(5)  # Wait for deletion to propagate

print(f"Creating new index '{index_name}' with metric='dotproduct' for hybrid search...")
pc.create_index(
    name=index_name,
    dimension=1536,
    metric="dotproduct",
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"
    )
)

print("Index created successfully!")
