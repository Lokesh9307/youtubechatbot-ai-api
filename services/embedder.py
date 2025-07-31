from fastembed.embedding import DefaultEmbedding

def get_embedder():
    return DefaultEmbedding(model_name="BAAI/bge-small-en-v1.5")
