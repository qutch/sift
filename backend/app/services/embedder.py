from ollama import embed, embeddings
from pathlib import Path
from classes.File import File

class Embedder:

    def __init__(self):
        self.targetDimension = 1024
        self.model = 'qwen3-embedding:0.6b'

    def EmbedFile(self, file: File):
        embeddings = []
        for chunk in file.chunks:
            embeddings.append(self.EmbedChunk(chunk))
        print(f"Embedded {len(embeddings)} chunks successfully with {len(embeddings[0])} dimensions")
        return embeddings

    def EmbedFileBatch(self, file: File):
        embeddings = []
        embedResponse = embed(model=self.model, input=file.chunks, dimensions=self.targetDimension)
        embeddings = embedResponse['embeddings']
        print(f"\nEmbedded {len(embeddings)} chunks successfully with {len(embeddings[0])} dimensions\n")
        return embeddings

    def EmbedChunk(self, chunk: str):
        return embed(model=self.model, input=chunk, dimensions=self.targetDimension)