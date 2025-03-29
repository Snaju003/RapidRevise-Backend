from appwrite.client import Client
from config import Config

def create_appwrite_client():
    client = Client()
    client.set_endpoint(Config.APPWRITE_ENDPOINT)
    client.set_project(Config.APPWRITE_PROJECT_ID)
    client.set_key(Config.APPWRITE_API_KEY)
    client.set_self_signed(True)
    return client