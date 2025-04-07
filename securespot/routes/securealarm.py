import os
import json
from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from securespot.database import user_collection
from bson import ObjectId
import google.generativeai as genai
import PIL.Image

# Define the upload directory and ensure it exists.
upload_dir = "uploads"
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir)

router = APIRouter()

from fastapi.responses import StreamingResponse
import asyncio

async def event_stream():
    """Generate server-sent events asynchronously."""
    count = 0
    while True:
        await asyncio.sleep(2)  # Simulate delay
        yield {"data": f"Event {count}\n\n"}
        count +=858904

@router.get("/events")
async def sse_endpoint():
    return StreamingResponse(event_stream(), media_type="text/event-stream")


from fastapi import FastAPI, WebSocket, WebSocketDisconnect


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Wait for text data from the client
            data = await websocket.receive_text()
            print(f"Received: {data}")
            # Process the received message and send a response
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        print("Client disconnected")

@router.post("/securitycheck")
async def security_check(image: UploadFile = File(...)):
    # # Verify the provided token exists in the user_collection
    # user = await user_collection.find_one({"token": token})
    # if not user:
    #     raise HTTPException(status_code=401, detail="Invalid token")

    # Generate a unique filename for the image
    unique_id = str(ObjectId())
    image_filename = f"{unique_id}_{image.filename}"
    image_path = os.path.join(upload_dir, image_filename)

    # Save the image to the specified directory
    with open(image_path, "wb") as buffer:
        buffer.write(await image.read())

    # Define the enhanced prompt for Generative AI with a detailed JSON output format.
    prompt = """
You are an expert agent specialized in detecting suspicious activity from images. 
You are provided with an image that may or may not depict a parking area. 
Analyze the image and determine if any suspicious or criminal activity is present.
If the image is not related to a parking area, return a null value for activity, confidence, alert_level, and an empty list for detected_objects with a message indicating it is irrelevant.

Provide your analysis in the following JSON output format:
{
  "activity": "yes if suspicious or criminal activity is detected, otherwise no",
  "message": "Provide a detailed reasoning in 20 words or less",
  "confidence": "A number between 0 and 100 indicating your confidence level in int",
  "detected_objects": ["A list of objects detected in the image, or an empty list if none"],
  "alert_level": "One of Critical, High, Medium, or Low based on the severity of the detected activity"
}
    """

    # Open the image using PIL
    pil_image = PIL.Image.open(image_path)

    # Configure the Generative AI model
    GOOGLE_API_KEY = "AIzaSyDh9lrdGmPIw_V6QyoWp5lEenGPVJ8oV2w"
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(
        'gemini-2.0-flash',
        generation_config={"response_mime_type": "application/json"}
    )

    # Generate content using the prompt and image
    response = model.generate_content([prompt, pil_image])

    # Parse the response text to a JSON object so the frontend receives structured data
    try:
        analysis = json.loads(response.text)
    except Exception as e:
        analysis = {"error": "Response could not be parsed as JSON", "raw_response": response.text}

    return {
        "status": True,
        "message": "Successfully detected parking",
        "data": analysis
    }
