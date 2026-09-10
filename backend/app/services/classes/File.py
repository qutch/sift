from classes.Vector import Vector
from datetime import datetime
from pathlib import Path

class File:
    def __init__(self, text: str, path: Path, name: str, extension: str):
        self.text = text
        self.path = path
        self.name = name
        self.type = extension

        self.summary: str = ""
        self.size: int = 0
        self.lastOpened: datetime = None
        self.lastEdited: datetime = None
        self.createdAt: datetime = None
        self.chunks: list[str] = []
        self.vectors: list[Vector] = []

    def SetSummary(self, summary: str):
        self.summary = summary

    def SetSize(self, size: int):
        self.size = size

    def SetLastOpened(self, lastOpened: datetime):
        self.lastOpened = lastOpened

    def SetLastEdited(self, lastEdited: datetime):
        self.lastEdited = lastEdited

    def SetCreatedAt(self, createdAt: datetime):
        self.createdAt = createdAt

    def SetChunks(self, chunks: list[str]):
        self.chunks = chunks

    def AddVector(self, vector: Vector):
        self.vectors.append(vector)

    # Returns formatted data in the format expected by the lancedb metadata schema
    def FormattedMetadata(self):
        data = {
            'fileType': self.type,
            'fileName': self.name,
            'filePath': str(self.path),
            'summary': self.summary,
            'size': self.size,
            'lastOpened': self.lastOpened,
            'lastEdited': self.lastEdited,
            'createdAt': self.createdAt
        }
        return data

    def __str__(self):
        print(f"--=====-- {self.name} --=====--")
        print(f"PATH: {self.path}")
        print(f"FILE TYPE: {self.type}")
        print(f"SUMMARY: {self.summary}")
        print(f"SIZE: {self.size} bytes")
        print(f"LAST OPENED: {self.lastOpened}")
        print(f"LAST EDITED: {self.lastEdited}")
        print(f"CREATED AT: {self.createdAt}")
        for idx, chunk in enumerate(self.chunks):
                    print(f"CHUNK #{idx} ---> {chunk}")
        print("--=====--==========--======--\n")
        return ""
