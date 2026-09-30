import json
from pathlib import Path
import lancedb as lance
import pyarrow as pa
from classes import File, Vector, FileType
from embedder import Embedder

# Remembers where the user chose to keep their data, so the backend can
# reconnect on its own after a restart
CONFIG_PATH = Path.home() / "Library" / "Application Support" / "Sift" / "config.json"

# Raised when something needs the database before the user has picked where to store it
class DatabaseNotConfigured(Exception):
    pass

class DBService():

    def __init__(self):
        self._db = None
        self.uri = None
        self.embedder = Embedder()

        savedLocation = self.LoadSavedLocation()
        if savedLocation:
            try:
                self.EstablishDatabase(savedLocation)
            except Exception as e:
                print(f"Couldn't reopen database at {savedLocation}: {e}")

    @property
    def db(self):
        if self._db is None:
            raise DatabaseNotConfigured("No data location has been chosen yet")
        return self._db

    @property
    def isConfigured(self) -> bool:
        return self._db is not None

    # Connects to (creating if needed) the LanceDB database in the given folder
    def EstablishDatabase(self, location: str):
        path = Path(location).expanduser()
        path.mkdir(parents=True, exist_ok=True)

        self._db = lance.connect(str(path))
        self.uri = str(path)
        self.InitializeDatabase()

    # Switches to the data folder the user picked and remembers it for next launch
    def SetLocation(self, location: str):
        self.EstablishDatabase(location)

        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps({"databaseLocation": self.uri}))

    def LoadSavedLocation(self) -> str | None:
        try:
            return json.loads(CONFIG_PATH.read_text()).get("databaseLocation")
        except (OSError, ValueError):
            return None

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
        if not file.vectors:
            return

        # One add per file: every add commits a new version/fragment in LanceDB
        table = self.db.open_table("sift-vectors")
        table.add([vector.FormattedVector() for vector in file.vectors])

    # Inserts metadata into the DB from a file object
    def InsertMetadata(self, file: File):
        table = self.db.open_table("sift-metadata")
        table.add([file.FormattedMetadata()])

    # Compacts the small fragments left behind by many inserts
    def OptimizeTables(self):
        for name in ("sift-vectors", "sift-metadata"):
            self.db.open_table(name).optimize()

    # Returns general info on the database's current state
    def GetInfo(self):
        vec_table = self.db.open_table("sift-vectors")
        meta_table = self.db.open_table("sift-metadata")

        print("vectors:", vec_table.count_rows())
        print("metadata:", meta_table.count_rows())

    # Returns metadata rows for the given file paths, keyed by filePath.
    # Used to show each search result's stored summary.
    def GetMetadataForFiles(self, filePaths: list[str]) -> dict[str, dict]:
        if not filePaths:
            return {}

        meta_table = self.db.open_table("sift-metadata")
        # Filter inside LanceDB rather than loading the whole table, since
        # this runs on every search. SQL strings escape ' by doubling it
        quoted = ", ".join("'" + path.replace("'", "''") + "'" for path in filePaths)
        rows = meta_table.search().where(f"filePath IN ({quoted})").limit(len(filePaths) * 2).to_list()

        return {row['filePath']: row for row in rows}

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

    # Returns the chunks closest to the query, searched by LanceDB
    def GetChunks(self, query: str, limit: int = 5):
        vec_table = self.db.open_table("sift-vectors")

        embeddedQuery = self.embedder.EmbedChunk(query).embeddings[0]

        return vec_table.search(embeddedQuery).limit(limit).to_list()
