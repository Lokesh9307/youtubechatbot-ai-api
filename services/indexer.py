from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.embeddings.fastembed.base import FastEmbedEmbedding
from llama_index.core import Settings
from services.llmgroq import query_groq
import uuid
import asyncio
import os 
import tempfile


# settings for LLama_index for default error
Settings.llm = None

def build_index(transcript: str):
    temp_filename = f"{uuid.uuid4()}.txt"
    local_temp_path = os.path.join(tempfile.gettempdir(), temp_filename)

    try:
        with open(local_temp_path, "w", encoding="utf-8") as f:
            f.write(transcript)

        documents = SimpleDirectoryReader(input_files=[local_temp_path]).load_data()
        embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
        index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)

    finally:
        if os.path.exists(local_temp_path):
            os.remove(local_temp_path)

    return index

def query_index(index, question: str):
    nodes = index.as_query_engine(similarity_top_k=5).retrieve(question)
    context = "\n".join([n.get_content() for n in nodes])
    full_prompt = f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
    response = asyncio.run(query_groq(full_prompt))
    return response
