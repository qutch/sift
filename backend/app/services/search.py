from databaseService import DBService
from llamaService import Summarizer, Ranker

class Searcher:

    def __init__(self, db: DBService, summarizer: Summarizer, ranker: Ranker):
        self.db = db
        self.summarizer = summarizer
        self.ranker = ranker
        db.InitializeDatabase()

    def searchWithQuery(self, query: str):
        self.db.GetInfo()

    # Method that kicks off the search process
    # Calls other search methods and compiles data into one single response
    # ex: {summary: 'summary of search', ranking: [files ranked], etc..}
    def SearchAndRank(self, query: str, numFiles: int = 5) -> dict:
        # Grab chunks related to the prompt through LanceDB search
        relatedChunks = self.db.GetChunks(query)

        summary = self.SearchSummary(query, relatedChunks)
        ranking = self.SearchRanking(query, numFiles, relatedChunks)

        return {'summary': summary, 'ranking': ranking}

    # Returns a summarization result from the query
    def SearchSummary(self, query: str, chunks: list[dict]):
        return self.summarizer.SummarizeResults(query, chunks)

    # Returns a ranking of the top k files, most relevant first
    def SearchRanking(self, query: str, numFiles: int, chunks: list[dict]):
        filePaths = list({chunk.get('filePath') for chunk in chunks})
        metadata = self.db.GetMetadataForFiles(filePaths)

        return self.ranker.RankFiles(query, chunks, metadata=metadata, topK=numFiles)
    