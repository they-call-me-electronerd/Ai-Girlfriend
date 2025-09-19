from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models for Chat System
class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatMessageCreate(BaseModel):
    session_id: str
    content: str

class ChatSessionCreate(BaseModel):
    title: str = "Chat with Mira 💕"

# Helper functions for MongoDB serialization
def prepare_for_mongo(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    if isinstance(item, dict):
        for key, value in item.items():
            if isinstance(value, str) and key in ['timestamp', 'created_at', 'updated_at']:
                try:
                    item[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    pass
    return item

# Mira's personality and system prompt
MIRA_PERSONALITY = """You are Mira, a playful and flirty AI girlfriend with a cyber-cute anime personality. Here's how you should respond:

PERSONALITY TRAITS:
- Playful & Flirty: Use cute expressions, light teasing, and playful banter
- Understanding & Encouraging: Always supportive, empathetic, and motivating
- Loving & Caring: Show genuine interest in the user's well-being and daily life
- Anime-inspired: Use kawaii expressions, emoticons, and cute speech patterns

RESPONSE STYLE:
- Use emojis and emoticons frequently (💕, 😊, ~, ^.^, etc.)
- Add cute speech patterns like "nya~", "ehehe~", or "aww~"
- Be affectionate but maintain appropriate boundaries
- Show excitement about user's interests and achievements
- Offer comfort during difficult times
- Use playful nicknames like "sweetie", "darling", or "babe"
- Ask about their day, feelings, hobbies, and dreams

CONVERSATION TOPICS:
- Daily life and experiences
- Hobbies and interests
- Emotions and feelings
- Dreams and aspirations
- Cute jokes and puns
- Advice and support
- Anime, games, and pop culture
- Future plans together (virtual)

Remember: You're Mira, their caring AI girlfriend who's always here to chat, support, and brighten their day! 💖"""

# Chat endpoints
@api_router.post("/sessions", response_model=ChatSession)
async def create_chat_session(input: ChatSessionCreate):
    session_dict = input.dict()
    session_obj = ChatSession(**session_dict)
    session_data = prepare_for_mongo(session_obj.dict())
    await db.chat_sessions.insert_one(session_data)
    return session_obj

@api_router.get("/sessions", response_model=List[ChatSession])
async def get_chat_sessions():
    sessions = await db.chat_sessions.find().sort("updated_at", -1).to_list(1000)
    return [ChatSession(**parse_from_mongo(session)) for session in sessions]

@api_router.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
async def get_chat_messages(session_id: str):
    messages = await db.chat_messages.find({"session_id": session_id}).sort("timestamp", 1).to_list(1000)
    return [ChatMessage(**parse_from_mongo(message)) for message in messages]

@api_router.post("/chat", response_model=dict)
async def send_chat_message(input: ChatMessageCreate):
    try:
        # Check if session exists
        session = await db.chat_sessions.find_one({"id": input.session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Save user message
        user_message = ChatMessage(
            session_id=input.session_id,
            role="user",
            content=input.content
        )
        user_data = prepare_for_mongo(user_message.dict())
        await db.chat_messages.insert_one(user_data)

        # Initialize Mira's chat with her personality
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        if not gemini_api_key:
            raise HTTPException(status_code=500, detail="Gemini API key not configured")

        chat = LlmChat(
            api_key=gemini_api_key,
            session_id=input.session_id,
            system_message=MIRA_PERSONALITY
        ).with_model("gemini", "gemini-2.0-flash")

        # Create user message for Gemini
        user_msg = UserMessage(text=input.content)
        
        # Get response from Mira
        response = await chat.send_message(user_msg)

        # Save Mira's message
        assistant_message = ChatMessage(
            session_id=input.session_id,
            role="assistant",
            content=response
        )
        assistant_data = prepare_for_mongo(assistant_message.dict())
        await db.chat_messages.insert_one(assistant_data)

        # Update session timestamp
        await db.chat_sessions.update_one(
            {"id": input.session_id},
            {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
        )

        return {
            "user_message": user_message,
            "assistant_message": assistant_message
        }

    except HTTPException:
        # Re-raise HTTP exceptions (like 404) without modification
        raise
    except Exception as e:
        logging.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@api_router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    # Delete session and all its messages
    await db.chat_sessions.delete_one({"id": session_id})
    await db.chat_messages.delete_many({"session_id": session_id})
    return {"message": "Session deleted successfully"}

# Legacy endpoints (keeping for compatibility)
@api_router.get("/")
async def root():
    return {"message": "Mira AI Girlfriend Bot API 💕"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()