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
            ".cpp", ".json", ".xml", ".toml",
            ".pdf", ".docx", ".png", ".jpg", ".jpeg",
        )
        self.chunk_size = 1000
        self.chunk_overlap = 100

        # Directories that hold generated/dependency files rather than the
        # user's own documents. Hidden directories (".git", ".venv", ...) are
        # skipped too
        self.skip_dirs = {
            "node_modules", "venv", "env", "__pycache__", "build", "dist",
            "target", "Pods", "DerivedData", "Library", "site-packages",
        }

        # Size caps in bytes: plain text/code files are read fully into memory,
        # so they get a tighter cap than PDFs/Word docs/images
        self.max_text_bytes = 5 * 1024 * 1024
        self.max_binary_bytes = 50 * 1024 * 1024
        self.binary_types = (".pdf", ".docx", ".png", ".jpg", ".jpeg")

    # Finds, parses, chunks, embeds, and stores every target file in a folder
    def process_folder(self, folder_path: Path) -> list[Path]:
        target_files = self.find_target_files(folder_path)

        self.parser.resetTrackingProgress()
        self.parser.setTotalFilesToParse(len(target_files))
        self.parser.StartProcessing()

        try:
            for file_path in target_files:
                self.process_file(file_path)

            # Each insert commits a new LanceDB fragment, so merge them once per run
            self.db.OptimizeTables()
        finally:
            self.parser.StopProcessing()

        return target_files

    # Builds out a list of files matching target file types, skipping
    # dependency/build/hidden directories and files over the size caps
    def find_target_files(self, folder_path: Path) -> list[Path]:
        target_files = []

        for root, dirs, files in folder_path.walk(top_down=True):
            # Pruning dirs in place stops the walk from descending into them
            dirs[:] = [d for d in dirs if d not in self.skip_dirs and not d.startswith(".")]

            for file in files:
                if not file.endswith(self.target_types):
                    continue

                path = root / file
                try:
                    size = path.stat().st_size
                except OSError:
                    # Broken symlink or unreadable file
                    continue

                maxBytes = self.max_binary_bytes if file.endswith(self.binary_types) else self.max_text_bytes
                if size > maxBytes:
                    print(f"skipping {path}: {size} bytes is over the size cap")
                    continue

                target_files.append(path)

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
