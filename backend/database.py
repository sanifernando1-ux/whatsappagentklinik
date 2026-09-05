import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]


def clean(doc):
    """Remove Mongo _id so documents are JSON serializable."""
    if not doc:
        return doc
    doc.pop("_id", None)
    return doc


def clean_list(docs):
    return [clean(d) for d in docs]
