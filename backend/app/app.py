import queue
import sys
import threading
from pathlib import Path

# The service modules import each other as top-level modules
# (e.g. `from databaseService import DBService`), so put services/ on the path
sys.path.insert(0, str(Path(__file__).parent / "services"))

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from services.search import Searcher
from services.databaseService import DBService, DatabaseNotConfigured
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

# Anything that touches LanceDB before the user has chosen a data folder
# gets a 409 the frontend can recognize, rather than a generic 500
@app.exception_handler(DatabaseNotConfigured)
def database_not_configured(request: Request, exc: DatabaseNotConfigured):
    return JSONResponse(status_code=409, content={"detail": str(exc)})

@app.get("/")
def read_root():
    return {"Able to read the root": "Yippee!"}

class DatabaseLocation(BaseModel):
    path: str

# Where LanceDB is storing data, or null if the user hasn't chosen yet
@app.get("/database/location")
def get_database_location() -> dict:
    return {"path": db.uri}

# Points LanceDB at the folder the user chose, creating the tables there if needed
@app.put("/database/location")
def set_database_location(location: DatabaseLocation) -> dict:
    # Switching underneath a running indexer would split its writes across two databases
    if parser.GetStatus()["isProcessing"]:
        raise HTTPException(status_code=409, detail="Can't change the data location while indexing")
    try:
        db.SetLocation(location.path)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f"Can't use {location.path}: {e}")
    return {"path": db.uri}

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

# Folders waiting to be indexed. A single worker thread drains this one folder
# at a time, so overlapping requests (e.g. several folders added at once)
# queue up instead of running concurrent indexers on shared Parser state
indexQueue: queue.Queue[Path] = queue.Queue()

def indexWorker():
    while True:
        path = indexQueue.get()
        try:
            indexer.process_folder(path)
        except Exception as e:
            print(f"Indexing failed for {path}: {e}")
        finally:
            indexQueue.task_done()
            # process_folder marks the parser idle when it finishes; if more
            # folders are waiting, flip it back so the status doesn't flicker
            if not indexQueue.empty():
                parser.StartProcessing()

threading.Thread(target=indexWorker, daemon=True).start()

# Queue a folder for processing and return right away; progress is reported by /status
@app.post("/process/{folder_path:path}")
def add_folder(folder_path: str) -> dict:
    # Paths come in without their leading '/', so add it back
    path = Path("/" + folder_path.lstrip("/"))

    # Fail now rather than inside the worker thread, where the frontend wouldn't see it
    if not db.isConfigured:
        raise DatabaseNotConfigured("No data location has been chosen yet")

    # Mark as processing now so /status doesn't read idle before the worker picks this up
    parser.StartProcessing()
    indexQueue.put(path)

    # TODO: Add this folder to the watcher's list

    return {"status": "queued"}

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

