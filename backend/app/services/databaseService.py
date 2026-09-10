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
                pa.field("vector", pa.list_(pa.float32(), 1024)),
                pa.field("filePath", pa.string()),
                pa.field("chunkIndex", pa.int16()),
                pa.field("chunkText", pa.string()),
            ]
        )
        # Create the table for vectors
        self.db.create_table("sift-vectors", schema=vectorSchema, mode="overwrite")

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
        # Create the metadata table
        self.db.create_table("sift-metadata", schema=metadataSchema, mode="overwrite")

    def InsertVectors(self, file: File):
        table = self.db.open_table("sift-vectors")
        for vector in file.vectors:
            table.add([vector.FormattedVector()])

    def InsertMetadata(self, file: File):
        table = self.db.open_table("sift-metadata")
        table.add([file.FormattedMetadata()])

    def GetInfo(self):
        db = lance.connect("/users/hutch/desktop/example_lancedb")

        vec_table = db.open_table("sift-vectors")
        meta_table = db.open_table("sift-metadata")

        print("vectors:", vec_table.count_rows())
        print("metadata:", meta_table.count_rows())