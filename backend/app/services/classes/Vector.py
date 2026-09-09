from classes.File import File
from pathlib import Path

class Vector:
    """
    Class that holds a single vector based on a chunk of text.
    Contains:
    - Embedded vector
    - File path
    - Chunk index
    - Chunk text
    """
    
    def __init__(self, vector: list[float], filePath: Path, index: int, text: str):
        self.vector: list[float] = vector
        self.filePath: Path = filePath
        self.chunkIndex = index
        self.chunkText = text

    def SetVector(self, vector: list[float]):
        self.vector = vector

    # Returns formatted data in the format expected by the lancedb vector schema
    def FormattedVector(self):
        data = {}
        
        # Set data
        data['vector'] = self.vector
        data['filePath'] = self.filePath
        data['chunkIndex'] = self.chunkIndex
        data['chunkText'] = self.chunkText

        return data
