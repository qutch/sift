from typing import Iterator
from databaseService import DBService
from llamaService import Summarizer

class Searcher:

    def __init__(self, db: DBService, summarizer: Summarizer):
        self.db = db
        self.summarizer = summarizer

        # Chunks to pull from the vector search. Several chunks usually come
        # from the same file, so this needs to be well above numFiles to
        # surface enough distinct files
        self.chunkLimit = 20
        # Chunks fed to the result summary, to keep that LLM call short
        self.summaryChunks = 5

    # Kicks off the search process, yielding each stage as soon as it's ready
    # so the caller can show results before the slow LLM summary finishes:
    # 1. {'type': 'results', 'files': [...]}   - vector search only, near-instant
    # 2. {'type': 'summary', 'summary': '...'} - LLM summary of the matched chunks
    # A failed summary is skipped rather than failing the whole search, since
    # the vector results are still useful on their own
    def Search(self, query: str, numFiles: int = 5) -> Iterator[dict]:
        # Grab chunks related to the prompt through LanceDB search, closest first
        relatedChunks = self.db.GetChunks(query, self.chunkLimit)

        # Keep the numFiles files with the closest chunks, in order of their best chunk
        topPaths = list(dict.fromkeys(chunk['filePath'] for chunk in relatedChunks))[:numFiles]
        chunks = [chunk for chunk in relatedChunks if chunk['filePath'] in topPaths]
        metadata = self.db.GetMetadataForFiles(topPaths)

        yield {'type': 'results', 'files': [self.QuickResult(path, metadata.get(path, {})) for path in topPaths]}

        if not topPaths:
            return

        try:
            yield {'type': 'summary', 'summary': self.SearchSummary(query, chunks[:self.summaryChunks])}
        except Exception as e:
            print(f"Search: summary failed ({e})")

    # A search result built only from what's already in LanceDB; the summary
    # is the one generated for the file at index time
    def QuickResult(self, filePath: str, metadata: dict) -> dict:
        return {
            'filePath': filePath,
            'fileName': metadata.get('fileName'),
            'summary': metadata.get('summary'),
        }

    # Returns a summarization result from the query
    def SearchSummary(self, query: str, chunks: list[dict]):
        return self.summarizer.SummarizeResults(query, chunks)
