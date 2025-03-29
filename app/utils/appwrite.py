from appwrite.client import Client
from appwrite.services.databases import Databases
from flask import current_app

def get_client():
    """
    Get initialized Appwrite client
    """
    client = Client()
    client.set_endpoint(current_app.config['APPWRITE_ENDPOINT']) \
          .set_project(current_app.config['APPWRITE_PROJECT_ID']) \
          .set_key(current_app.config['APPWRITE_API_KEY'])
    return client

def get_database_service():
    """
    Get initialized Appwrite Database service
    """
    client = get_client()
    return Databases(client)