from fastapi import APIRouter, HTTPException, Depends
from jose import jwt
from bson import ObjectId
from securespot.models import User, Login, GetUserDetails, SendingUserOTP, GetOPTStatus
from securespot.database import user_collection
from securespot.config import settings
from securespot.auth import hash_password, create_access_token, verify_password
from securespot.help import get_user_by_email
from securespot.services.email_auth import sending_email, generate_otp
from datetime import datetime, timedelta
import textwrap

router = APIRouter()


@router.post("/signup")
async def signup(user: User):
    try:
        if user.password and user.password != user.confirm_password:
            return {"status": False, "message": "Passwords do not match"}
        existing_user = await user_collection.find_one({"email": user.email})
        if existing_user:
            return {"status": False, "message": "User with this email already exists"}
        # verify_status = verify_email_smtp(email=user.email)
        # if verify_status:
        hashed_password = await hash_password(user.password) if user.password else None

        new_user = {
            "_id": str(ObjectId()),
            "name": user.name,
            "email": user.email,
            "password": hashed_password,
            "token": None,
            "otp": None,
            "otp_expiry": None,
            "is_verified": False,
            "joining_date": datetime.utcnow().strftime("%m-%d-%Y")
        }

        await user_collection.insert_one(new_user)
        return {"status": True, "message": "User registered successfully"}

    except Exception as e:
        return {"status": False, "message": "An error occurred during signup"}


@router.post("/login")
async def login(data: Login):
    try:
        # If the request contains email and password
        if data.email and data.password:
            user = await get_user_by_email(data.email)

            if not user:
                return {"status": False, "message": "Invalid credentials"}

            # Verify the password with the hashed password in DB
            if not await verify_password(data.password, user['password']):
                return {"status": False, "message": "Invalid email or password"}

            if user['is_verified']:

                # Generate a new token for the existing user
                token_data = {"sub": user["email"]}
                token = await create_access_token(token_data)

                # Update the token in the database
                await user_collection.update_one({"email": user["email"]}, {"$set": {"token": token}})
                return {"status": True, "message": "Login successfully", "token": token}
            else:
                return {"status": False, "message": "Kindly authenticate your account with otp."}


    except Exception as e:
        return {"status": False, "message": "An error occurred during login"}


@router.post("/get_user_details")
async def get_user_details(data: GetUserDetails):
    try:
        user = await user_collection.find_one({"token": data.token})
        if not user:
            return {"status": False, "message": "Invalid token"}

        token = data.token
        # Decode the token to extract the email
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email = payload.get("sub")
            if not email:
                return {"status": False, "message": "Invalid token"}
        except jwt.JWTError:
            return {"status": False, "message": "Invalid token"}

        # Fetch the user by email
        user = await user_collection.find_one({"email": email})
        if not user:
            return {"status": False, "message": "User not found"}

        # Exclude the token before returning the data
        user.pop("token", None)
        user.pop("password", None)
        user.pop("otp", None)
        user.pop("otp_expiry", None)
        user.pop("is_verified", None)
        return {"status": True, "message": "Successfully Retrieved Data", "data": user}

    except Exception as e:
        return {"status": False, "message": "An error occurred while retrieving user details"}


@router.post("/send_otp")
async def sending_otp(data: SendingUserOTP):
    try:
        user = await user_collection.find_one({"email": data.email})
        if not user:
            return {"status": False, "message": "Invalid token"}
        otp = await generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=5)
        update_data = {
            'otp': otp,
            'otp_expiry': otp_expiry,
            'is_verified': False
        }
        await user_collection.update_one({"email": data.email}, {"$set": update_data})
        code = otp
        email_subject = 'Your One-Time Login Code'

        # Use textwrap.dedent to remove extra indentation from the email text
        email_text = textwrap.dedent(f"""\
            # Hello,

            Your secure one-time login code is: {code}

            Please use this code to access your Securespot account. If you did not request this code, please disregard this email.

            Best regards,
            **Securespot Team**
            """)
        status = await sending_email(email_subject, email_text, user['email'])
        if status:
            return {"status": True, "message": "Send OTP Successfully"}

        else:
            return {"status": False, "message": "Sending OTP Error"}

    except Exception as e:
        return {"status": False, "message": "An error occurred while sending OTP"}


@router.post("/verify_otp_code")
async def verifying_user_otp(data: GetOPTStatus):
    try:
        user = await user_collection.find_one({"email": data.email})
        if not user:
            return {"status": False, "message": "Invalid token"}
        otp_input = data.otp
        # Check if the OTP has expired
        if datetime.utcnow() > user['otp_expiry']:
            raise HTTPException(status_code=404, detail="OTP expired")
            return {"status": False, "message": "OTP expired"}

        # Verify the provided OTP
        if otp_input != user['otp']:
            return {"status": False, "message": "Invalid OTP"}

        await user_collection.update_one({"email": user["email"]}, {"$set": {"is_verified": True}})
        return {"status": True, "message": "Successfully Authenticate"}

    except Exception as e:
        return {"status": False, "message": "An error occurred while authenticating OTP"}

