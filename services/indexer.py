from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.embeddings.fastembed.base import FastEmbedEmbedding
from llama_index.core import Settings
from services.llmgroq import query_groq
from google.cloud import storage
import uuid
import asyncio
import os 

# settings for LLama_index for default error
Settings.llm = None

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GCS_TEMP_FOLDER = os.getenv("GCS_TEMP_FOLDER")

def build_index(transcript: str):
    # Create a unique temp filename
    temp_filename = f"{uuid.uuid4()}.txt"
    local_temp_path = f"/tmp/{temp_filename}"

    # Save locally (you can skip this and upload directly from memory if needed)
    # with open(local_temp_path, "w", encoding="utf-8") as f:
    #     f.write(transcript)

    # Upload to GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(f"{GCS_TEMP_FOLDER}/{temp_filename}")
    blob.upload_from_filename(local_temp_path)

    # Optional: Set metadata to auto-delete later
    # (actual deletion is handled by lifecycle rule in bucket)

    # Load document directly from local file before deleting it
    documents = SimpleDirectoryReader(input_files=[local_temp_path]).load_data()
    embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
    index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)

    # Clean up local file
    os.remove(local_temp_path)

    return index

def query_index(index, question: str):
    nodes = index.as_query_engine(similarity_top_k=5).retrieve(question)
    context = "\n".join([n.get_content() for n in nodes])
    full_prompt = f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
    response = asyncio.run(query_groq(full_prompt))
    return response
