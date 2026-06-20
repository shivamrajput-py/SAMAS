import os
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document

def test_pinecone():
    print("Testing Pinecone Integration...")
    
    # 1. Check Env Vars
    pinecone_key = os.environ.get("PINECONE_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    index_name = os.environ.get("PINECONE_INDEX_NAME", "samas-index")
    
    if not pinecone_key or not openrouter_key:
        print("Error: Missing API Keys in .env")
        return
        
    print(f"Index Name: {index_name}")
    print("Initializing Embeddings via OpenRouter...")
    
    try:
        embedder = OpenAIEmbeddings(
            openai_api_base=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            openai_api_key=openrouter_key,
            model="openai/text-embedding-3-small"
        )
        
        # Test basic embedding
        test_text = "This is a test document for Pinecone."
        print("Generating test embedding...")
        vector = embedder.embed_query(test_text)
        print(f"Generated vector of length {len(vector)}.")
        
        # Test Upsert
        print("Attempting to upsert to Pinecone...")
        doc = Document(page_content=test_text, metadata={"test": True, "job_id": "test-123"})
        PineconeVectorStore.from_documents([doc], embedder, index_name=index_name)
        print("Upsert successful!")
        
        # Test Search
        print("Attempting to search Pinecone...")
        vectorstore = PineconeVectorStore(index_name=index_name, embedding=embedder)
        results = vectorstore.similarity_search_with_score("test document", k=1)
        print(f"Search successful! Found {len(results)} results.")
        if results:
            print(f"Top result score: {results[0][1]} - Content: {results[0][0].page_content}")
            
        print("\nSUCCESS: Pinecone is fully integrated and working alongside the embedder!")
        
    except Exception as e:
        print(f"\nERROR: Pinecone integration test failed: {e}")

if __name__ == "__main__":
    test_pinecone()
