# app/services.py
from appwrite.client import Client
from appwrite.services.databases import Databases
from flask import current_app

def create_appwrite_client():
    client = Client()
    config = current_app.config
    client.set_endpoint(config['APPWRITE_ENDPOINT'])
    client.set_project(config['APPWRITE_PROJECT'])
    client.set_key(config['APPWRITE_API_KEY'])
    client.set_self_signed()  # Only use in development when using self-signed certificates
    return client

def get_documents(collection: str):
    """
    Retrieve documents from a specified collection.
    Use the collection name (e.g., 'User', 'Community', or 'Resources').
    """
    client = create_appwrite_client()
    database = Databases(client)
    db_id = current_app.config['APPWRITE_DB']
    # The list_documents method requires the database ID and collection ID.
    # You might store your actual Appwrite collection IDs in your config if they differ from collection names.
    result = database.list_documents(db_id, collection)
    return result
