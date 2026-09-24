from databaseService import DBService

class Searcher:

    def __init__(self, db: DBService):
        self.db = db
        db.InitializeDatabase()

    def searchWithQuery(self, query: str):
        self.db.GetInfo()
    
    # Method that kicks off the search process
    # Calls other search methods and compiles data into one single response
    # ex: {summary: 'summary of search', ranking: [files ranked], etc..}
    def Search(self, query: str):
        # Grab chunks related to the prompt through LanceDB search
        relatedChunks = self.db.GetChunks(query)
        relatedFiles = []

        # Find files from chunks
        for chunk in relatedChunks:
            relatedFiles.append(chunk.get('filePath'))

        # Filter out any duplicate entries
        relatedFiles = list(set(relatedFiles))

    # Returns a summarization result from the query
    def SearchSummary(self, query: str, chunks: list[dict]):
        pass

    # Returns a ranking of the top k files
    def SearchRanking(self, query: str, numFiles: int, chunks: list[dict]):
        pass
    