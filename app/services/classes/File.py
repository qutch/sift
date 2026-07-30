import FileType

class File:
    def __init__(self, path: str, name: str, extension: str, type: FileType):
        self.path = path
        self.name = name
        self.parsed = False