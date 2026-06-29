import os
import uuid
from typing import List, Dict, Any, Tuple
from pinecone import Pinecone
from pinecone_text.sparse import BM25Encoder
from app.config import PINECONE_API_KEY, PINECONE_INDEX_NAME

# Create singletons
_bm25_encoder = None
_pinecone_index = None

def get_bm25_encoder() -> BM25Encoder:
    global _bm25_encoder
    if _bm25_encoder is None:
        _bm25_encoder = BM25Encoder().default()
    return _bm25_encoder

def get_pinecone_index(index_name: str = None):
    global _pinecone_index
    idx_name = index_name or PINECONE_INDEX_NAME
    
    if _pinecone_index is None:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        _pinecone_index = pc.Index(idx_name)
    return _pinecone_index

def hybrid_upsert(texts: List[str], metadatas: List[Dict[str, Any]], embedder, index_name: str = None):
    """Upsert documents into Pinecone using Hybrid Search (Dense + Sparse)."""
    if not texts:
        return
        
    index = get_pinecone_index(index_name)
    
    bm25 = get_bm25_encoder()
    
    print(f"   [Hybrid Search] Encoding {len(texts)} documents...")
    dense_vecs = embedder.embed_documents(texts)
    sparse_vecs = bm25.encode_documents(texts)
    
    vectors = []
    for i in range(len(texts)):
        # Generate a unique ID for each document if not provided in metadata
        doc_id = str(uuid.uuid4())
        metadata = metadatas[i] if i < len(metadatas) else {}
        metadata["text"] = texts[i]
        
        vectors.append({
            "id": doc_id,
            "values": dense_vecs[i],
            "sparse_values": sparse_vecs[i],
            "metadata": metadata
        })
        
    print(f"   [Hybrid Search] Upserting to Pinecone index: {index_name}")
    index.upsert(vectors=vectors)


def hybrid_search(query: str, embedder, top_k: int = 10, index_name: str = None, alpha: float = 0.5) -> List[Tuple[Dict[str, Any], float]]:
    """
    Query Pinecone using Hybrid Search.
    alpha = 0.0 -> Keyword search only (BM25)
    alpha = 1.0 -> Semantic search only (Dense)
    alpha = 0.5 -> Balanced Hybrid Search
    """
    index = get_pinecone_index(index_name)
    
    bm25 = get_bm25_encoder()
    
    dense_vec = embedder.embed_query(query)
    sparse_vec = bm25.encode_queries(query)
    
    # Weight the vectors using the alpha parameter
    hdense = [v * alpha for v in dense_vec]
    hsparse = {
        "indices": sparse_vec["indices"],
        "values": [v * (1.0 - alpha) for v in sparse_vec["values"]]
    }
    
    result = index.query(
        vector=hdense,
        sparse_vector=hsparse,
        top_k=top_k,
        include_metadata=True
    )
    
    # Return list of (metadata, score)
    return [(match.metadata, match.score) for match in result.matches]
