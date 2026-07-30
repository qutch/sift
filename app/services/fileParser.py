from pathlib import Path

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


    def ParseFile(self, filePath: str) -> str:
        path = Path(filePath)
        fileType = path.suffix[1:]
        
        if fileType in self.textExtensions:
            return self.ParseText(path)

        elif fileType in self.codeExtensions:
            return self.ParseText(path)

        elif fileType in self.pdfExtensions:
            return self.ParsePDF(path)

        # elif fileType in self.imageExtensions:
        #     return self.ParseImage(path)

        else:
            return None


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
        
        pages = self.pdfParser.is_complex(filePath)
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


if __name__ == "__main__":
    p = Parser()
    userInput = input("Enter a file path: ")
    output = p.ParseFile(userInput)