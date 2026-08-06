from classes.File import File

class Vector:
    def __init__(self, vector, file):
        self.vector: list[float] = vector
        self.file: File = file

    def SetVector(self, vector: list[float]):
        self.vector = vector

    def SetFile(self, file: File):
        self.file = file

    def SetVectorAndFile(self, vector: list[float], file: File):
        self.vector = vector
        self.file = file