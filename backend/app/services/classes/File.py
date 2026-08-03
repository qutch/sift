from datetime import datetime
from pathlib import Path

class File:
    def __init__(self, text: str, path: Path, name: str, extension: str):
        self.text = text
        self.path = path
        self.name = name
        self.type = extension

        self.summary: str
        self.size: int
        self.lastOpened: datetime
        self.lastEdited: datetime
        self.createdAt: datetime

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

    def __str__(self):
        print(f"--=====-- {self.name} --=====--")
        print(f"PATH: {self.path}")
        print(f"FILE TYPE: {self.type}")
        print(f"SUMMARY: {self.summary}")
        print(f"SIZE: {self.size} bytes")
        print(f"LAST OPENED: {self.lastOpened}")
        print(f"LAST EDITED: {self.lastEdited}")
        print(f"CREATED AT: {self.createdAt}")
        print("--=====--==========--======--\n")
        return ""
