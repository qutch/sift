from ollama import embed, embeddings
from pathlib import Path

class Embedder:

    def __init__(self):
        self.embeddingSize = 1024
        self.model = 'qwen3-embedding:0.6b'

    def EmbedFile(self, path: Path):
        pass

    def EmbedChunk(self, chunk: str):
        pass