import sys
from pathlib import Path

# The service modules import each other as top-level modules
# (e.g. `from databaseService import DBService`), so put services/ on the path
sys.path.insert(0, str(Path(__file__).parent / "services"))

from fastapi import FastAPI, HTTPException, Query
from services.search import Searcher
from services.databaseService import DBService
from services.llamaService import Summarizer, Ranker
from services.indexer import Indexer
from services.fileParser import Parser
from services.chunker import Chunker
from services.embedder import Embedder

app = FastAPI()
db = DBService()
summarizer = Summarizer()
ranker = Ranker()
searcher = Searcher(db, summarizer, ranker)
parser = Parser()
chunker = Chunker()
embedder = Embedder()
indexer = Indexer(db, parser, chunker, embedder)

@app.get("/")
def read_root():
    return {"Able to read the root": "Yippee!"}

# Basic search with a query, e.g. /search?q=data structures
# (a query param rather than a path segment so queries can contain '/')
@app.get("/search")
def search(q: str = Query(min_length=1), numFiles: int = 5):
    return searcher.SearchAndRank(q, numFiles)

# Grab a single file's metadata
@app.get("/file/{file_path:path}")
def get_file(file_path: str) -> dict:
    # Paths come in without their leading '/', so add it back
    path = "/" + file_path.lstrip("/")
    metadata = db.GetMetadataForFiles([path])
    if path not in metadata:
        raise HTTPException(status_code=404, detail="File has not been indexed")
    return metadata[path]

# Process a folder
@app.post("/process/{folder_path:path}")
def add_folder(folder_path: str) -> None:
    # Paths come in without their leading '/', so add it back
    path = Path("/" + folder_path.lstrip("/"))

    # Index the folder and any sub-folders
    indexer.process_folder(path)

    # TODO: Add this folder to the watcher's list

    return {"status": "indexing"}

# Current indexing progress, polled by the frontend to drive its processing indicator
@app.get("/status")
def get_status() -> dict:
    return parser.GetStatus()

# Metadata for every file that has been indexed so far
@app.get("/files")
def get_files() -> list[dict]:
    return db.GetAllMetadata()

# Wipes all indexed vectors and metadata from LanceDB
@app.delete("/database")
def clear_database() -> dict:
    db.ClearDatabase()
    return {"status": "cleared"}

