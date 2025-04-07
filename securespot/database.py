from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

client_db = AsyncIOMotorClient(settings.MONGO_DETAILS)
database = client_db.user_db
user_collection = database.users
vehicle_collection = database.vehicles
ride_offer_collection = database.ride_offers
ride_request_collection = database.ride_requests
chats_collection = database.chats
parking_collection = database.parking_management


