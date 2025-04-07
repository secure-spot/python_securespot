import os
import secrets
import urllib.parse

# Generate a secure random secret key
secret_key = '4567890sdfghjk456789dfg567'
username = 'nidaeman0002'
password = 'DWDOt7lfz22FDLK0'

# URL-encode the username and password
encoded_username = urllib.parse.quote_plus(username)
encoded_password = urllib.parse.quote_plus(password)
class Settings:
    MONGO_DETAILS = os.getenv("MONGO_DETAILS", f"mongodb+srv://{encoded_username}:{encoded_password}@cluster0.mdoa1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "34128153484-2lfk3rb9pn431vscnsmb252t0n4oibqh.apps.googleusercontent.com")
    SECRET_KEY = os.getenv("SECRET_KEY", secret_key)
    ALGORITHM = "HS256"
    map_api = os.getenv("map_api", "AIzaSyA4WeE-BvNOhIA7g3sxQQ_bVlEmGu2adhs")
    gemini_api = os.getenv('gemini_api',"AIzaSyA6cpd0kH1fm6JDuJE8YHMcc9X4RVTYEk4")

settings = Settings()
