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
            collection_id=Config.APPWRITE_COMMUNITY_COLLECTION_ID,
            document_id='unique()',  # Let Appwrite generate an ID
            data={
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "user": data.get("user", "")  # Just the user ID reference
            }
        )
        
        # Filter the response to only include the desired fields
        filtered_result = {
            "$id": result.get("$id"),
            "name": result.get("name"),
            "description": result.get("description"),
            "user": {}
        }
        
        user_obj = result.get("user", {})
        if isinstance(user_obj, dict):
            filtered_result["user"] = {
                "$id": user_obj.get("$id"),
                "name": user_obj.get("name")
            }
        
        return jsonify(filtered_result), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@community_bp.route('/', methods=['GET'])
def get_all_communities():
    """
    Fetch all Community documents from Appwrite.
    Returns a JSON object with key "community" and an array of community data.
    Each community data contains id, createdAt, updatedAt, description, name, and user:{id, name}.
    """
    client = create_appwrite_client()
    databases = Databases(client)

    try:
        result = databases.list_documents(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_COMMUNITY_COLLECTION_ID
        )
        # Filter and transform the documents
        communities = []
        for doc in result.get("documents", []):
            filtered_doc = {
                "id": doc.get("$id"),
                "name": doc.get("name"),
                "description": doc.get("description"),
                "user": {},
                "createdAt": doc.get("$createdAt"),
                "updatedAt": doc.get("$updatedAt"),
            }
            # If the user field exists and is a dictionary, filter it
            user_obj = doc.get("user", {})
            if isinstance(user_obj, dict):
                filtered_doc["user"] = {
                    "id": user_obj.get("$id"),
                    "name": user_obj.get("name")
                }
            communities.append(filtered_doc)

        # Build the final response object
        response = {
            "community": communities
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@community_bp.route('/<community_id>', methods=['GET'])
def get_community(community_id):
    """
    Fetch a single Community document by its ID and return only the selected fields.
    """
    client = create_appwrite_client()
    databases = Databases(client)

    try:
        result = databases.get_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_COMMUNITY_COLLECTION_ID,
            document_id=community_id
        )
        
        # Filter the result to only include the desired fields
        filtered_result = {
            "id": result.get("$id"),
            "name": result.get("name"),
            "description": result.get("description"),
            "createdAt": result.get("$createdAt"),
            "updatedAt": result.get("$updatedAt"),
            "user": {}
        }
        
        user_obj = result.get("user", {})
        if isinstance(user_obj, dict):
            filtered_result["user"] = {
                "id": user_obj.get("$id"),
                "name": user_obj.get("name")
            }
            
        return jsonify(filtered_result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@community_bp.route('/<community_id>', methods=['PUT'])
def update_community(community_id):
    """
    Update an existing Community document.
    Expects JSON with updated fields.
    Checks if the provided user_id exists in the Appwrite User collection.
    Returns only: id, name, description, and user { id, name }.
    """
    data = request.json or {}
    
    client = create_appwrite_client()
    databases = Databases(client)
    
    # Extract user_id from the request data
    user_id = data.get("user", "").strip()
    if not user_id:
        return jsonify({"error": "User id not provided."}), 400

    # Check the user_id exists in the Appwrite User collection
    try:
        # This will raise an exception if the user is not found
        user_doc = databases.get_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_USER_COLLECTION_ID,
            document_id=user_id
        )
    except Exception as e:
        return jsonify({"error": "User not found in Appwrite user collections."}), 404

    try:
        # Update the community document
        result = databases.update_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_COMMUNITY_COLLECTION_ID,
            document_id=community_id,
            data={
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "user": user_id
            }
        )
        
        # Filter the result to include only the desired fields
        filtered_result = {
            "id": result.get("$id"),
            "name": result.get("name"),
            "description": result.get("description"),
            "user": {}
        }
        
        user_obj = result.get("user", {})
        if isinstance(user_obj, dict):
            filtered_result["user"] = {
                "id": user_obj.get("$id"),
                "name": user_obj.get("name")
            }
        else:
            filtered_result["user"] = {"id": user_id, "name": ""}
        
        return jsonify(filtered_result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

