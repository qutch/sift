from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
def read_root():
    return {"Able to read the root": "Yippee"}

@app.get("/search/{search_query}")
def read_search(search_query: str):
    return {"Search Query": search_query}