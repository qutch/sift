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
        # Vector distances (qwen3-embedding, L2) for deciding which excerpts are
        # close enough to summarize. On the test folder real matches landed at
        # 0.5-1.17, while queries with nothing relevant never got closer than
        # 1.23. Excerpts much further than the best match are left out too, so
        # the summary doesn't pad itself with loosely related files
        self.maxSummaryDistance = 1.2
        self.summaryDistanceSpread = 0.25

    # A search happens in two stages so the caller can show results before the
    # slow LLM summary finishes (see app.py's /search):
    # 1. Results: vector search only, near-instant
    # 2. Summary: LLM summary of the excerpts close enough to be worth it
    # Returns the results stage, plus the chunks to hand to Summary
    def Results(self, query: str, numFiles: int = 5) -> tuple[dict, list[dict]]:
        # Grab chunks related to the prompt through LanceDB search, closest first
        relatedChunks = self.db.GetChunks(query, self.chunkLimit)

        # Keep the numFiles files with the closest chunks, in order of their best chunk
        topPaths = list(dict.fromkeys(chunk['filePath'] for chunk in relatedChunks))[:numFiles]
        metadata = self.db.GetMetadataForFiles(topPaths)

        results = {'type': 'results', 'files': [self.QuickResult(path, metadata.get(path, {})) for path in topPaths]}
        return results, self.SummaryChunks(relatedChunks, topPaths)

    # The closest chunks from the result files, dropping any too far from the
    # query (or from the best match) to be relevant
    def SummaryChunks(self, chunks: list[dict], filePaths: list[str]) -> list[dict]:
        chunks = [chunk for chunk in chunks if chunk['filePath'] in filePaths]
        if not chunks:
            return []

        cutoff = min(self.maxSummaryDistance, chunks[0]['_distance'] + self.summaryDistanceSpread)
        return [chunk for chunk in chunks if chunk['_distance'] <= cutoff][:self.summaryChunks]

    # Returns the summary stage. With nothing close enough to summarize, says
    # so right away instead of having the LLM stretch to connect unrelated files
    async def Summary(self, query: str, chunks: list[dict]) -> dict:
        if not chunks:
            return {'type': 'summary', 'summary': "No files closely match your search."}
        return {'type': 'summary', 'summary': await self.summarizer.SummarizeResults(query, chunks)}

    # A search result built only from what's already in LanceDB; the summary
    # is the one generated for the file at index time
    def QuickResult(self, filePath: str, metadata: dict) -> dict:
        return {
            'filePath': filePath,
            'fileName': metadata.get('fileName'),
            'summary': metadata.get('summary'),
        }
