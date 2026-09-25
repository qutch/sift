from fastapi import FastAPI, Query
from pydantic import BaseModel
from services.search import Searcher
from services.databaseService import DBService
from services.llamaService import Summarizer, Ranker
from pathlib import Path

app = FastAPI()
db = DBService()
summarizer = Summarizer()
ranker = Ranker()
searcher = Searcher(db, summarizer, ranker)

@app.get("/")
def read_root():
    return {"Able to read the root": "Yippee"}

# Basic search with a query
@app.get("/search/{search_query}")
def search(search_query: str):
    return searcher.SearchAndRank(search_query)

# Grab a single file's metadata
@app.get("/file/{file_path}")
def get_file(file_path: Path) -> dict[str, dict]:
    return db.GetMetadataForFiles(str(file_path))

@app("/file/{file_path}")
def open_file(file_path: Path) -> int:
    try:
        # Try to open file given
        Path.open(file_path, "r")
        return 0
    except FileNotFoundError:
        raise FileNotFoundError("File could not be found")