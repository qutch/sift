# Responsible for indexing files in a folder.
# Given a folder of files the indexer:
# 1. Goes through the files and parses, chunks, and saves chunks with file metadata in an array
# 2. Passes array of file data to embedder --> uploader

from pathlib import Path
from databaseService import DBService
from fileParser import Parser
from chunker import Chunker
from embedder import Embedder

class Indexer:

    def __init__(self, db: DBService, parser: Parser, chunker: Chunker, embedder: Embedder):
        self.db = db
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder

        self.target_types = (
            ".txt", ".md", ".py", ".java", ".c",
            ".cpp", ".json", ".xml", ".env", ".toml",
            ".pdf", ".docx", ".png", ".jpg", ".jpeg",
        )
        self.chunk_size = 1000
        self.chunk_overlap = 100

    # Finds, parses, chunks, embeds, and stores every target file in a folder
    def process_folder(self, folder_path: Path) -> list[Path]:
        target_files = self.find_target_files(folder_path)

        self.parser.resetTrackingProgress()
        self.parser.setTotalFilesToParse(len(target_files))
        self.parser.StartProcessing()

        try:
            for file_path in target_files:
                self.process_file(file_path)
        finally:
            self.parser.StopProcessing()

        return target_files

    # Builds out a list of files matching target file types
    def find_target_files(self, folder_path: Path) -> list[Path]:
        target_files = []

        for root, dirs, files in folder_path.walk(top_down=True):
            for file in files:
                if file.endswith(self.target_types):
                    target_files.append(Path(f"{str(root)}/{file}"))

        return target_files

    # Parses a single file, then chunks, embeds, and stores it
    def process_file(self, file_path: Path):
        parsedFile = self.parser.ParseFile(file_path)
        if parsedFile is None:
            return

        chunks = self.chunker.ChunkText(parsedFile.text, self.chunk_overlap, self.chunk_size)
        parsedFile.SetChunks(chunks)

        self.embedder.EmbedFileBatch(parsedFile)

        self.db.InsertMetadata(parsedFile)
        self.db.InsertVectors(parsedFile)
