from pathlib import Path
from datetime import datetime
from classes.File import File
from llamaService import Summarizer

# Import parsing services
import pymupdf4llm as pypdf
from liteparse import LiteParse

class Parser:

    def __init__(self):
        # Extensions initialization
        self.textExtensions = ["txt", "md"]
        self.codeExtensions = ["py", "java", "c", "cpp", "json", "xml", "env", "toml"]
        self.pdfExtensions = ["pdf", "docx"]
        self.imageExtensions = ["png", "jpg", "jpeg", ""]
        
        self.heavyPDFParser = LiteParse(ocr_enabled=True, output_format="text")
        self.lightPDFParser = LiteParse(ocr_enabled=False, output_format="text")


    # Parses a file and returns data as a File object
    def ParseFile(self, filePath: Path) -> File:
        path = Path(filePath)
        fileType = path.suffix[1:]

        metadata = self.GetFileMetadata(path)

        parsedFile: File = None
        parsedText: str = None

        if fileType in self.textExtensions:
            parsedText = self.ParseText(path)

        elif fileType in self.codeExtensions:
            parsedText = self.ParseText(path)

        elif fileType in self.pdfExtensions:
            parsedText = self.ParsePDF(path)

        if parsedText != None:
            parsedFile = File(parsedText, Path(filePath), metadata.get('name'), metadata.get('type'))
            
            parsedFile.SetCreatedAt(metadata.get('createdAt'))
            parsedFile.SetLastOpened(metadata.get('lastOpened'))
            parsedFile.SetLastEdited(metadata.get('lastEdited'))
            parsedFile.SetSize(metadata.get('size'))
            parsedFile.SetSummary(self.GetSummary(parsedText))

        else:
            print('something went wrong')
            return None

        return parsedFile


    def ParseText(self, filePath: Path) -> str:
        print("parsing text: " + filePath.name)
        output = ""
        with open(filePath, "r", encoding="utf-8") as f:
            for line in f.readlines():
                output += line + "\n"
        f.close()

        return output

    def ParsePDF(self, filePath: Path) -> str:
        print("parsing pdf: " + filePath.name)
        print("file location: " + str(filePath))
        
        pages = LiteParse.is_complex(self.heavyPDFParser, filePath)
        if any(p.needs_ocr for p in pages):
            output = self.heavyPDFParser.parse(filePath)
            text = ""
            for page in output.pages:
                text += page.text + "\n"
            return text
        else:
            output = self.lightPDFParser.parse(filePath)
            return output

    def ParseWord(self, filePath: Path) -> str:
        print("parsing word: " + filePath)
        
        output = self.pdfParser.parse(filePath)
        text = ""
        for page in output.pages:
            text += page.text + "\n"
        return output

    def ParseImage(self, filePath: Path) -> str:
        print("parsing image: " + filePath)
        return None

    def GetFileMetadata(self, filePath: Path):
        # Return metadata such as: size and type
        type = filePath.suffix[1:]
        name = filePath.name
        location = filePath
        size = filePath.stat().st_size # in bytes
        createdAt = datetime.fromtimestamp(filePath.stat().st_birthtime).strftime('%Y-%m-%d %H:%M:%S')
        lastEdited = datetime.fromtimestamp(filePath.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        lastOpened = datetime.fromtimestamp(filePath.stat().st_atime).strftime('%Y-%m-%d %H:%M:%S')

        return {'name': name, 'type': type,'path': location, 'size': size, 'created': createdAt, 'lastEdited': lastEdited, 'lastOpened': lastOpened}


    def GetSummary(self, text: str) -> str:
        s = Summarizer()
        return s.Summarize(text)