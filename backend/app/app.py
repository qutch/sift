from fastapi import FastAPI, Query
from pydantic import BaseModel
from services.search import Searcher
from services.databaseService import DBService
from services.llamaService import Summarizer, Ranker

app = FastAPI()
db = DBService()
summarizer = Summarizer()
ranker = Ranker()
searcher = Searcher(db, summarizer, ranker)

@app.get("/")
def read_root():
    return {"Able to read the root": "Yippee"}

@app.get("/search/{search_query}")
def search(search_query: str):
    return searcher.SearchAndRank(search_query)