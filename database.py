from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client: AsyncIOMotorClient = None
db = None

# In-memory fallback storage when MongoDB is unavailable
meetings_store = []
use_memory_store = False
_id_counter = 0


async def connect_to_mongo():
    global client, db, use_memory_store
    try:
        if MONGO_URI:
            client = AsyncIOMotorClient(
                MONGO_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
            )
            await client.admin.command('ping')
            db = client.ai_meeting_summarizer
            use_memory_store = False
            print("Connected to MongoDB successfully!")
        else:
            print("MongoDB URI not found. Using in-memory storage.")
            use_memory_store = True
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        print("Falling back to in-memory storage.")
        client = None
        db = None
        use_memory_store = True


async def save_meeting(meeting_data: dict):
    """Save meeting data to MongoDB or in-memory store with auto timestamp."""
    global meetings_store, _id_counter

    # Auto-add created_at timestamp
    meeting_data["created_at"] = datetime.now(timezone.utc).isoformat()

    if db is not None:
        await db.meetings.insert_one(meeting_data)
    else:
        _id_counter += 1
        meeting_data["_id"] = str(_id_counter)
        meetings_store.insert(0, meeting_data)  # newest first


async def get_meetings(limit: int = 10):
    """Get meetings from MongoDB or in-memory store."""
    if db is not None:
        cursor = db.meetings.find().sort("_id", -1).limit(limit)
        meetings = await cursor.to_list(length=limit)
        for m in meetings:
            m["_id"] = str(m["_id"])
        return meetings
    else:
        return meetings_store[:limit]


async def get_meeting_by_id(meeting_id: str):
    """Get a single meeting by its ID (for Q&A feature)."""
    if db is not None:
        from bson import ObjectId
        try:
            meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
            if meeting:
                meeting["_id"] = str(meeting["_id"])
            return meeting
        except Exception:
            return None
    else:
        for m in meetings_store:
            if str(m.get("_id", "")) == meeting_id:
                return m
        return None


async def delete_meeting(meeting_id: str):
    """Delete a meeting from MongoDB or in-memory store."""
    global meetings_store
    if db is not None:
        from bson import ObjectId
        try:
            result = await db.meetings.delete_one({"_id": ObjectId(meeting_id)})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting meeting from MongoDB: {e}")
            return False
    else:
        # In-memory delete
        original_length = len(meetings_store)
        meetings_store = [m for m in meetings_store if str(m.get("_id", "")) != meeting_id]
        return len(meetings_store) < original_length


async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")
