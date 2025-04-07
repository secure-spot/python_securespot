from langchain.memory import ConversationTokenBufferMemory
from securespot.database import chats_collection, user_collection
from securespot.services.chathandler import SecureChatbot
from securespot.models import ChatResponse, GetChatResponse
from fastapi import APIRouter
from langchain_google_genai import ChatGoogleGenerativeAI
from securespot.config import settings
import getpass
import os
bot = SecureChatbot()
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = settings.gemini_api
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)
router = APIRouter()


@router.post("/get_response_securebot")
async def get_response_securebot(data: ChatResponse):
    try:
        existing_user = await user_collection.find_one({"token": data.token})
        if not existing_user:
            return {"status": False, "message": "User not found"}

        user_id = existing_user['_id']
        # Await the load_chat function.
        db_chat_history = await bot.load_chat(user_id)
        if not db_chat_history:
            await bot.create_chat(user_id)
            db_chat_history = await bot.load_chat(user_id)

        memory = ConversationTokenBufferMemory(llm=llm, max_token_limit=8000)
        for entry in db_chat_history:
            memory.save_context({"input": entry["question"]}, {"output": entry["response"]})

        chat_history = memory.load_memory_variables({}).get('history', [])
        answer = await bot.get_response(data.query, chat_history)  # your function that calls the LLM
        await bot.update_chat(user_id, data.query, answer)

        return {"status": True, "message": answer}
    except Exception as e:
        return {"status": False, "message": "An error occurred while generating response"}



@router.post("/getchat_securebot")
async def get_chat_securebot(data: GetChatResponse):
    try:
        existing_user = await user_collection.find_one({"token": data.token})
        if not existing_user:
            return {"status": False, "message": "User not found"}

        user_id = existing_user['_id']
        db_chat_history = await bot.load_chat(user_id)

        return {"status": True, "chat_history": db_chat_history}
    except Exception as e:
        return {"status": False, "message": "An error occurred while getting chathistory"}
