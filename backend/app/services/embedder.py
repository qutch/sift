import time
from ollama import embed, embeddings
from pathlib import Path
from classes.File import File
from classes.Vector import Vector

class Embedder:

    def __init__(self):
        self.targetDimension = 1024
        self.model = 'qwen3-embedding:0.6b'

        # Chunks per Ollama request, and the pause between requests in seconds
        self.batchSize = 16
        self.pauseSeconds = 0.1

    def EmbedFile(self, file: File):
        embeddings = []
        for chunk in file.chunks:
            embeddings.append(self.EmbedChunk(chunk))
        print(f"Embedded {len(embeddings)} chunks successfully with {len(embeddings[0])} dimensions")
        return embeddings

    # Embeds a file's chunks in small slices rather than one giant request, so
    # a large file can't spike memory, and pauses between slices so the GPU
    # can yield to the rest of the system
    def EmbedFileBatch(self, file: File):
        embeddings = []

        for start in range(0, len(file.chunks), self.batchSize):
            batch = file.chunks[start:start + self.batchSize]
            embedResponse = embed(model=self.model, input=batch, dimensions=self.targetDimension)
            embeddings.extend(embedResponse['embeddings'])

            if start + self.batchSize < len(file.chunks):
                time.sleep(self.pauseSeconds)

        for idx, embeddedChunk in enumerate(embeddings):
            newVec = Vector(embeddedChunk, file.path, idx, file.chunks[idx])
            # Add the new vector object to the file's list
            file.AddVector(newVec)

        if embeddings:
            print(f"\nEmbedded {len(embeddings)} chunks successfully with {len(embeddings[0])} dimensions\n")
        return embeddings

    def EmbedChunk(self, chunk: str):
        return embed(model=self.model, input=chunk, dimensions=self.targetDimension)