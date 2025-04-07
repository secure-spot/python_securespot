from securespot.database import user_collection

async def get_user_by_email(email: str):
    return await user_collection.find_one({"email": email})