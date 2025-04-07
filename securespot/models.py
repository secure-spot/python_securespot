from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class User(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str
    confirm_password: str

class Login(BaseModel):
    email: EmailStr
    password: str

class GetUserDetails(BaseModel):
    token: str

class SendingUserOTP(BaseModel):
    email: str
class GetOPTStatus(BaseModel):
    otp: str
    email: str

class Vehicle(BaseModel):
    token: str
    model: str
    year: int
    color: str
    license_plate: str = None

class GetVehicleDetails(BaseModel):
    token: str

class RequestRide(BaseModel):
    token: str
    current_location: str
    destination_location: str

class ShareRide(BaseModel):
    token: str
    current_location: str
    destination_location: str
    available_seats: int

class StopShareRide(BaseModel):
    token: str

class SendRequestRide(BaseModel):
    token: str
    ride_offer_id: str

class ReceiveRequestRide(BaseModel):
    token:str

class ResponseRequestRide(BaseModel):
    token: str
    ride_request_id: str
    accept: bool
class RespondRideNotication(BaseModel):
    token: str

class CompleteRide(BaseModel):
    token: str

class ChatResponse(BaseModel):
    token: str
    query: str

class GetChatResponse(BaseModel):
    token: str

class ParkingData(BaseModel):
    token: str
    current_location: str

class NotifyParking(BaseModel):
    token: str
    status: bool
