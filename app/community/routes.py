# community/routes.py
from flask import request, jsonify
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.query import Query

from . import community_bp  # The blueprint from __init__.py
from config import Config

def create_appwrite_client():
    """
    Helper function to create and configure an Appwrite Client.
    """
    client = Client()
    client.set_endpoint(Config.APPWRITE_ENDPOINT)   # Your Appwrite endpoint
    client.set_project(Config.APPWRITE_PROJECT_ID)     # Your project ID
    client.set_key(Config.APPWRITE_API_KEY)         # Your API key
    client.set_self_signed(True)                    # Only use for dev/testing if self-signed
    return client

@community_bp.route('/', methods=['POST'])
def create_community():
    """
    Create (insert) a new Community document in Appwrite.
    Expects JSON in the body with fields like: name, description, user (relationship ID).
    """
    data = request.json or {}
    
    # Example JSON body:
    # {
    #   "name": "Flask Enthusiasts",
    #   "description": "A place to discuss Flask tips and tricks",
    #   "user": "user_document_id"   # The ID from your User collection if there's a relationship
    # }

    client = create_appwrite_client()
    databases = Databases(client)

    try:
        result = databases.create_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.COMMUNITY_COLLECTION_ID,
            document_id='unique()',  # Let Appwrite generate an ID
            data={
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "user": data.get("user", "")  # Relationship field if defined in Appwrite
            }
        )
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@community_bp.route('/', methods=['GET'])
def get_all_communities():
    """
    Fetch all Community documents from Appwrite.
    """
    client = create_appwrite_client()
    databases = Databases(client)

    try:
        result = databases.list_documents(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.COMMUNITY_COLLECTION_ID
        )
        # result is typically a dict with fields like: {'total': X, 'documents': [...]}
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@community_bp.route('/<community_id>', methods=['GET'])
def get_community(community_id):
    """
    Fetch a single Community document by its ID.
    """
    client = create_appwrite_client()
    databases = Databases(client)

    try:
        result = databases.get_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.COMMUNITY_COLLECTION_ID,
            document_id=community_id
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@community_bp.route('/<community_id>', methods=['PUT'])
def update_community(community_id):
    """
    Update an existing Community document.
    Expects JSON with updated fields.
    """
    data = request.json or {}
    
    client = create_appwrite_client()
    databases = Databases(client)

    try:
        # Example JSON body to update name or description:
        # {
        #   "name": "New Community Name",
        #   "description": "Updated description"
        # }
        result = databases.update_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.COMMUNITY_COLLECTION_ID,
            document_id=community_id,
            data={
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "user": data.get("user", "")
            }
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
