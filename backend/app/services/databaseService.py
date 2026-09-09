import lancedb as lance
import pyarrow as pa
from classes import File, Vector, FileType

class DBService():

    def __init__(self):
        self.db = None
        self.uri = None
        self.EstablishDatabase()
        self.InitializeDatabase()

    def EstablishDatabase(self):
        # Connect to local directory for database
        self.uri = "/users/hutch/desktop/example_lancedb"
        self.db = lance.connect(self.uri)

    def InitializeDatabase(self):
        # Create the vector schema
        vectorSchema = pa.schema(
            [
                pa.field("vector", pa.list_(pa.float16), 1024),
                pa.field("filePath", pa.string()), # Links vector to metadata --> is unique
            ]
        )
        # Create the table for vectors
        self.db.create_table("sift-vectors", schema=vectorSchema, mode="overwrite")

        # Create the metadata schema
        metadataSchema = pa.schema(
            [
                pa.field('fileType', pa.string()), # Links metadata to vector --> is unique
                pa.field("fileName", pa.string()),
                pa.field("filePath", pa.string()),
                pa.field("summary", pa.string()),
                pa.field("size", pa.int32()),
                pa.field("lastOpened", pa.date32()),
                pa.field("lastEdited", pa.date32()),
                pa.field("createdAt", pa.date32()),
            ]
        )
        # Create the metadata table
        self.db.create_table("sift-metadata", schema=metadataSchema, mode="overwrite")

    def InsertVector(self, table: str, vector: Vector):
        targetTable = self.db.open_table(table)
        targetTable.add(vector.Formatted())