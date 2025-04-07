import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from routes import users, vehicle, ridesharing, securealarm, parking, chatbot
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(users.router)
app.include_router(vehicle.router)
app.include_router(ridesharing.router)
app.include_router(securealarm.router)
app.include_router(parking.router)
app.include_router(chatbot.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
