import sys
from pathlib import Path

# The service modules import each other as top-level modules
# (e.g. `from databaseService import DBService`), so put services/ on the path
sys.path.insert(0, str(Path(__file__).parent / "services"))

from fastapi import FastAPI, HTTPException, Query
from search import Searcher
from databaseService import DBService
from llamaService import Summarizer, Ranker

app = FastAPI()
db = DBService()
summarizer = Summarizer()
ranker = Ranker()
searcher = Searcher(db, summarizer, ranker)

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
