import os
from fastapi import APIRouter, File, UploadFile
from securespot.database import user_collection, parking_collection
from securespot.models import ParkingData, NotifyParking
from bson import ObjectId
import PIL.Image
import google.generativeai as genai
from securespot.services.googlemap import get_distance
from securespot.services.ridemap import get_lat_long_from_address
from ultralytics import YOLO
import secrets
from datetime import datetime, timedelta
import json
# Define the upload directory and ensure it exists.
upload_dir = "uploads"
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir)

router = APIRouter()
model = YOLO("best.pt")
@router.post("/securitycheck")
async def security_check(image: UploadFile = File(...)):
    # Generate a unique filename for the image
    unique_id = str(ObjectId())
    image_filename = f"{unique_id}_{image.filename}"
    image_path = os.path.join(upload_dir, image_filename)

    # Save the image to the specified directory
    with open(image_path, "wb") as buffer:
        buffer.write(await image.read())

    image = PIL.Image.open(image_path)

    results = model(image)
    detected_class_indices = results[0].boxes.cls.cpu().numpy().astype(int)
    detected_class_names = [results[0].names[i] for i in detected_class_indices]
    # bounding_boxes = results[0].boxes.xyxy.cpu().numpy()

    prompt = f"""
You are an expert agent specializing in the analysis of car parking lot images. Your task is to accurately determine the parking status based on the image provided. Please follow these steps carefully:
1. Verify whether the image depicts a valid car parking lot scene. Set a flag "parking_valid" to true if valid; otherwise, false. set all values total_slot, occupied_slot , free_slots are set to be none
2. If the scene is valid, analyze the image to determine:
   - The total number of parking slots available ("total_slot"). very carefull determine proper logically
   - The number of slots that are occupied by cars ("occupied_slot"). It should be determined logically and answer should be accurate.
   - The number of slots that are free ("free_slots").  It should be determined logically and answer should be accurate.
3. Report the number of detected car instances separately as "detected_car_count". In this image, {len(detected_class_names)} car instances have been detected. This is just a context and you will also analyze the detetc car in image as your self if tis is wrong then correct it.
4. Provide any additional observations or message in a "message" field.
5. If the image is irrelevant (i.e., it is not related to a parking lot), then ignore the detected data and return null for all numerical fields and set "parking_valid" to false.
Provide your response strictly in the following JSON format without any additional text:
JSON OUT FORMAT:
{{
    "parking_valid": <boolean>,
    "total_slot": <integer or null>,
    "occupied_slot": <integer or null>,
    "free_slots": <integer or null>,
    "detected_car_count": <integer or null>,
    "message": <string or null> write messsge or reasoning here consist of 20 words
}}
"""
    GOOGLE_API_KEY = "AIzaSyDh9lrdGmPIw_V6QyoWp5lEenGPVJ8oV2w"
    genai.configure(api_key=GOOGLE_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-2.0-flash',
                                         generation_config={"response_mime_type": "application/json"})
    response = gemini_model.generate_content([prompt, image])
    return {"status": True, "message": "successfully detected parking", "data": f"{json.loads(response.text)}"}

EXPIRATION_MINUTES = 30

@router.post("/parkingtoken")
async def generate_token(data: ParkingData):
    # Verify the user token.
    user = await user_collection.find_one({"token": data.token})
    if not user:
        return {'status': False, 'message': 'Invalid token'}

    # Get latitude and longitude from the provided address.
    lat, lon = get_lat_long_from_address(data.current_location)
    if lat is None or lon is None:
        return {'status': False, 'message': 'Invalid current location'}

    # Calculate the distance and duration from a fixed reference point.
    reference_location = "33.779597, 72.351736"
    dist, dur = get_distance(reference_location, f"{lat}, {lon}")

    # Check if the duration is less than 30 minutes.
    if dur > EXPIRATION_MINUTES:
        return {
            "status": False,
            "message": "Duration to your location is greater than 30 minutes. Parking token will only be generated if duration is less than 30 minutes"
        }

    # Generate a new unique parking token.
    parking_token = secrets.token_hex(16)
    now = datetime.utcnow()

    # Check if user already has a parking token record.
    parking_record = await parking_collection.find_one({"user_id": user["_id"]})
    if parking_record:
        # Update existing record with a new token and reset creation time.
        update_fields = {
            "parking_token": parking_token,
            "current_location": data.current_location,
            "lat": lat,
            "lon": lon,
            "distance": dist,
            "duration": dur,
            "status": "active",  # Reset to active.
            "created_at": now,
            "notification_status": None
        }
        await parking_collection.update_one({"_id": parking_record["_id"]}, {"$set": update_fields})
    else:
        parking_doc = {
            "_id": str(ObjectId()),
            "user_id": user["_id"],
            "parking_token": parking_token,
            "current_location": data.current_location,
            "lat": lat,
            "lon": lon,
            "distance": dist,
            "duration": dur,
            "status": "active",  # "active" until notified or expired.
            "created_at": now,
            "notification_status": None
        }
        await parking_collection.insert_one(parking_doc)
    return {
        "status": True,
        "message": "Successfully generated parking token",
        "parking_token": parking_token
    }

@router.post("/parking_notify")
async def parking_notify(data: NotifyParking):
    """
    Combined endpoint that updates the parking notification status.
    If the token is older than 30 minutes without notification, it is marked as expired.
    Once notified, the token's status is updated to "parked".
    """
    # Verify the user token.
    user = await user_collection.find_one({"token": data.token})
    if not user:
        return {"status": False, "message": "Invalid token"}

    parking_record = await parking_collection.find_one({"user_id": user["_id"]})
    if not parking_record:
        return {"status": False, "message": "No parking token found for this user"}
    if parking_record["status"] == "parked":
        return {"status": False, "message": "You have already Parked"}

    created_at = parking_record.get("created_at")
    if not created_at:
        return {"status": False, "message": "Parking record missing creation time"}

    # Check if the parking token has expired.
    if datetime.utcnow() - created_at > timedelta(minutes=EXPIRATION_MINUTES):
        if parking_record.get("status") != "notified":
            await parking_collection.update_one(
                {"_id": parking_record["_id"]},
                {"$set": {"status": "expired"}}
            )
            return {
                "status": False,
                "message": "Parking token has expired due to no notification within 30 minutes"
            }

    # If a notification status is provided, update the record.
    if data.status:
        await parking_collection.update_one(
            {"_id": parking_record["_id"]},
            {"$set": {"notification_status": data.status, "status": "parked"}}
        )
        return {"status": True, "message": "Parking token notified successfully"}
    else:
        # If no update is provided, simply return the current status.
        return {
            "status": True,
            "message": "Parking token is active",
            "token_status": parking_record.get("status")
        }

@router.post("/exit_parking/{token}")
async def exit_parking(token: str):
    """
    Endpoint to exit parking by deleting the parking record.
    Exit is allowed only if the token status is "parked" or "expired".
    """
    # Verify the user token.
    user = await user_collection.find_one({"token": token})
    if not user:
        return {"status": False, "message": "Invalid token"}

    parking_record = await parking_collection.find_one({"user_id": user["_id"]})
    if not parking_record:
        return {"status": False, "message": "No parking token found for this user"}

    token_status = parking_record.get("status")
    if token_status in ["parked", "expired"]:
        await parking_collection.delete_one({"_id": parking_record["_id"]})
        return {"status": True, "message": "Exited parking successfully and token deleted"}
    else:
        return {"status": False, "message": "Cannot exit parking as the token is still active"}

@router.get("/parking_remaining/{token}")
async def parking_remaining(token: str):
    """
    Endpoint to return details about the active parking token along with the remaining time until expiration.
    If the token has expired, it will inform the caller.
    """
    # Verify the user token.
    user = await user_collection.find_one({"token": token})
    if not user:
        return {"status": False, "message": "Invalid token"}

    parking_record = await parking_collection.find_one({"user_id": user["_id"]})
    if not parking_record:
        return {"status": False, "message": "No parking token found for this user"}
    if parking_record["status"] == "parked":
        return {"status": False, "message": "You have already Parked. No need to check remaining time"}

    created_at = parking_record.get("created_at")
    if not created_at:
        return {"status": False, "message": "Parking record missing creation time"}

    elapsed = datetime.utcnow() - created_at
    remaining = timedelta(minutes=EXPIRATION_MINUTES) - elapsed

    if remaining.total_seconds() <= 0:
        # Update status if token is expired.
        if parking_record.get("status") != "expired":
            await parking_collection.update_one(
                {"_id": parking_record["_id"]},
                {"$set": {"status": "expired"}}
            )
        return {
            "status": False,
            "message": "Parking token has expired"
        }
    else:
        # Return remaining time in minutes (rounded to 2 decimals).
        remaining_minutes = round(remaining.total_seconds() / 60, 2)
        return {
            "status": True,
            "message": "Parking token is active",
            "remaining_time_minutes": remaining_minutes
        }