import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:3000/auth/google/callback')
    GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/auth'
    GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
    GOOGLE_USER_INFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'

    # Appwrite Configuration
    APPWRITE_ENDPOINT = os.environ.get('APPWRITE_ENDPOINT', 'https://cloud.appwrite.io/v1')
    APPWRITE_PROJECT_ID = os.environ.get('APPWRITE_PROJECT_ID')
    APPWRITE_API_KEY = os.environ.get('APPWRITE_API_KEY')
    APPWRITE_DATABASE_ID = os.environ.get('APPWRITE_DB')
    APPWRITE_USER_COLLECTION_ID = os.environ.get('USER_COLLECTION_ID')
    APPWRITE_COMMUNITY_COLLECTION_ID = os.environ.get('COMMUNITY_COLLECTION_ID')
    APPWRITE_RESOURCES_COLLECTION_ID = os.environ.get('RESOURCES_COLLECTION_ID')
