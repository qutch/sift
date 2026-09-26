import lancedb as lance
import pyarrow as pa
from classes import File, Vector, FileType
from embedder import Embedder

class DBService():

    def __init__(self):
        self.db = None
        self.uri = None
        self.EstablishDatabase()
        self.InitializeDatabase()
        self.embedder = Embedder()

    def EstablishDatabase(self):
        # Connect to local directory for database
        self.uri = "/users/hutch/desktop/example_lancedb"
        self.db = lance.connect(self.uri)

    def InitializeDatabase(self):
        # Create the vector schema
        vectorSchema = pa.schema(
            [
                pa.field("vector", pa.list_(pa.float32(), 1024)),
                pa.field("filePath", pa.string()),
                pa.field("chunkIndex", pa.int16()),
                pa.field("chunkText", pa.string()),
            ]
        )
        # Create the table for vectors, if it doesn't already exist -
        # mode="overwrite" here would wipe out previously indexed data
        # on every app startup
        self.db.create_table("sift-vectors", schema=vectorSchema, exist_ok=True)

        # Create the metadata schema
        metadataSchema = pa.schema(
            [
                pa.field('fileType', pa.string()),
                pa.field("fileName", pa.string()),
                pa.field("filePath", pa.string()),
                pa.field("summary", pa.string()),
                pa.field("size", pa.int32()),
                pa.field("lastOpened", pa.date32()),
                pa.field("lastEdited", pa.date32()),
                pa.field("createdAt", pa.date32()),
            ]
        )
        # Create the metadata table, if it doesn't already exist
        self.db.create_table("sift-metadata", schema=metadataSchema, exist_ok=True)
    
    # Inserts vectors into the DB from a file object
    def InsertVectors(self, file: File):
        table = self.db.open_table("sift-vectors")
        for vector in file.vectors:
            table.add([vector.FormattedVector()])

    # Inserts metadata into the DB from a file object
    def InsertMetadata(self, file: File):
        table = self.db.open_table("sift-metadata")
        table.add([file.FormattedMetadata()])

    # Returns general info on the database's current state
    def GetInfo(self):
        vec_table = self.db.open_table("sift-vectors")
        meta_table = self.db.open_table("sift-metadata")

        print("vectors:", vec_table.count_rows())
        print("metadata:", meta_table.count_rows())

    # Returns metadata rows for the given file paths, keyed by filePath.
    # Used to enrich ranking/summarization with each file's summary
    # instead of just its raw chunk text.
    def GetMetadataForFiles(self, filePaths: list[str]) -> dict[str, dict]:
        meta_table = self.db.open_table("sift-metadata")
        rows = meta_table.to_arrow().to_pylist()
        filePaths = set(filePaths)

        return {row['filePath']: row for row in rows if row['filePath'] in filePaths}

    # Returns metadata for every indexed file, used to back the frontend's
    # "processed files" list
    def GetAllMetadata(self) -> list[dict]:
        meta_table = self.db.open_table("sift-metadata")
        return meta_table.to_arrow().to_pylist()

    # Wipes all indexed vectors and metadata, then recreates the empty tables
    def ClearDatabase(self):
        self.db.drop_table("sift-vectors")
        self.db.drop_table("sift-metadata")
        self.InitializeDatabase()

    # Returns chunks related to the query, searched by LanceDB
    def GetChunks(self, query: str):
        vec_table = self.db.open_table("sift-vectors")
        meta_table = self.db.open_table("sift-metadata")

        embeddedQuery = self.embedder.EmbedChunk(query).embeddings[0]

        results = vec_table.search(embeddedQuery).limit(5).to_list()
        return results