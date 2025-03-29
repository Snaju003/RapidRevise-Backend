# config.py
import os

class Config:
    DEBUG = True
    # Appwrite settings
    APPWRITE_ENDPOINT = os.getenv('APPWRITE_ENDPOINT', 'http://localhost/v1')
    APPWRITE_PROJECT = os.getenv('APPWRITE_PROJECT', 'your_project_id')
    APPWRITE_API_KEY = os.getenv('APPWRITE_API_KEY', 'your_api_key')
    # Database and collections names
    APPWRITE_DB = os.getenv('APPWRITE_DB', 'RapidRevise_DB')
    USER_COLLECTION = 'User'
    COMMUNITY_COLLECTION = 'Community'
    RESOURCES_COLLECTION = 'Resources'
