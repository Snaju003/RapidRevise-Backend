# community/routes.py
from flask import request, jsonify, session
from appwrite.client import Client
from appwrite.services.databases import Databases
from app.services import create_appwrite_client
from appwrite.query import Query
from app.auth.utils import login_required

from . import community_bp
from config import Config

@community_bp.route('/', methods=['POST'])
@login_required
def create_community():
    """
    Create (insert) a new Community document in Appwrite.
    Expects JSON in the body with fields like: name, description.
    The user ID is taken from the session (login_required).
    """
    data = request.json or {}
    
    # Example JSON body:
    # {
    #   "name": "Flask Enthusiasts",
    #   "description": "A place to discuss Flask tips and tricks"
    # }
    # The user ID is retrieved from the session instead of the request.

    # Retrieve user_id from session (set during login)
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "No user_id found in session."}), 401
    
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
                # Use the user_id from session
                "user": user_id,
            }
        )
        
        # Filter the response to only include the desired fields
        filtered_result = {
            "$id": result.get("$id"),
            "name": result.get("name"),
            "description": result.get("description"),
            "createdAt": result.get("$createdAt"),
            "updatedAt": result.get("$updatedAt"),
            "communityResources":result.get("communityResources"),
            "user": {}
        }
        
        user_obj = result.get("user", {})
        if isinstance(user_obj, dict):
            filtered_result["user"] = {
                "$id": user_obj.get("$id"),
                "name": user_obj.get("name")
            }
        else:
            # If Appwrite returns only the user ID (string), handle accordingly
            filtered_result["user"] = {
                "$id": user_obj if isinstance(user_obj, str) else None,
                "name": ""
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
                "upvotes": doc.get("upvotes"),
                "downvotes": doc.get("downvotes"),
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
@login_required
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


@community_bp.route('/<community_id>', methods=['DELETE'])
@login_required
def delete_community(community_id):
    """
    Delete a Community document by its ID.
    """
    client = create_appwrite_client()
    databases = Databases(client)

    try:
        databases.delete_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_COMMUNITY_COLLECTION_ID,
            document_id=community_id
        )
        return jsonify({"message": "Community deleted successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@community_bp.route('/<community_id>/vote', methods=['PUT'])
@login_required
def vote_community(community_id):
    """
    Update the vote count for a Community document.
    Expects JSON with a field "vote":
        - If vote is 1, increment upvotes by 1.
        - If vote is -1, increment downvotes by 1.
    Returns a JSON object containing the community id, upvotes, and downvotes.
    """
    data = request.json or {}
    vote = data.get("vote")

    if vote not in [1, -1]:
        return jsonify({"error": "Invalid vote value. Must be 1 (upvote) or -1 (downvote)."}), 400

    client = create_appwrite_client()
    databases = Databases(client)

    try:
        # Retrieve the current community document
        doc = databases.get_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_COMMUNITY_COLLECTION_ID,
            document_id=community_id
        )
        
        # Retrieve current vote counts (default to 0 if not present)
        current_upvotes = doc.get("upvotes") or 0
        current_downvotes = doc.get("downvotes") or 0

        if vote == 1:
            new_upvotes = current_upvotes + 1
            new_downvotes = current_downvotes
        else:  # vote == -1
            new_upvotes = current_upvotes
            new_downvotes = current_downvotes + 1

        # Update the document with the new vote counts
        updated_doc = databases.update_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_COMMUNITY_COLLECTION_ID,
            document_id=community_id,
            data={
                "upvotes": new_upvotes,
                "downvotes": new_downvotes
            }
        )

        # Filter the response to only include the desired fields
        filtered_result = {
            "id": updated_doc.get("$id"),
            "upvotes": updated_doc.get("upvotes"),
            "downvotes": updated_doc.get("downvotes")
        }
        return jsonify(filtered_result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
