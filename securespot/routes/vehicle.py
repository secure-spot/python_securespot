from securespot.models import GetVehicleDetails, Vehicle
from fastapi import APIRouter, HTTPException
from securespot.database import vehicle_collection, user_collection
from bson import ObjectId

router = APIRouter()

@router.post("/register_vehicle")
async def add_vehicle(vehicle: Vehicle):
    """
    Endpoint to add a vehicle for a user.
    It checks if the user already has a vehicle.
    """
    try:
        # Check if the user already has a vehicle
        existing_user = await user_collection.find_one({"token": vehicle.token})
        if not existing_user:
            return {"status": False, "message": "User not found"}


        user_id = existing_user['_id']
        existing_vehicle = await vehicle_collection.find_one({"user_id": user_id})
        if existing_vehicle:
            return {"status": False, "message": "User already has a vehicle"}

        # Convert the Pydantic model to a dict and assign a new _id
        new_vehicle = vehicle.dict()
        new_vehicle.pop("token",None)
        new_vehicle["_id"] = str(ObjectId())
        new_vehicle["user_id"] = user_id


        # Insert the new vehicle into the database
        await vehicle_collection.insert_one(new_vehicle)
        return {"status": True, "message": "Vehicle registered successfully"}

    except Exception as e:
        return {"status": False, "message": "An error occurred while registering the vehicle"}


@router.post("/get_vehicle_details")
async def get_vehicle(data: GetVehicleDetails):
    """
    Endpoint to retrieve a vehicle by user_id.
    Returns a 404 error if no vehicle is found.
    """
    try:
        existing_user = await user_collection.find_one({"token": data.token})
        if not existing_user:
            return {"status": False, "message": "User not found"}
        user_id = existing_user['_id']
        vehicle = await vehicle_collection.find_one({"user_id": user_id})
        if not vehicle:
            return {"status": False, "message": "Vehicle not found for the given user"}
        return {"status": True, "message": "Successfully Retrieved Data", "data": vehicle}

    except Exception as e:
        return {"status": False, "message": "An error occurred while retrieving the vehicle"}
