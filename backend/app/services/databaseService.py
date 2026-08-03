import lancedb as lance
import pyarrow as pa
from lancedb.pydantic import LanceModel, Vector

class Vectors(LanceModel):
    vector: int
    summary: str

# Connect to local directory for database
uri = "/users/hutch/desktop/example_lancedb"
db = lance.connect(uri)

mainSchema = pa.schema(
    [
        pa.field("id", pa.uint16()),
        pa.field("vector", pa.list_(pa.float16), 1024),
        pa.field("fileName", pa.string()),
        pa.field('fileType', pa.string()),
        pa.field("filePath", pa.string()),
        pa.field("metadata", pa.struct(
            [
                pa.field("summary", pa.string()),
                pa.field("size", pa.int32()),
                pa.field("lastOpened", pa.date32()),
                pa.field("lastEdited", pa.date32()),
                pa.field("createdAt", pa.date32()),
            ]
        ))
    ]
)

mainTable = db.create_table("sift-vectors", schema=mainSchema, mode="overwrite")
