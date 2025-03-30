# app/resources/routes.py

from flask import request, jsonify
from appwrite.client import Client
from app.auth.utils import admin_required
from app.services import create_appwrite_client
from appwrite.services.databases import Databases
from appwrite.id import ID
from config import Config
from . import resources_bp

@resources_bp.route('/', methods=['POST'])
@admin_required
def create_resource():
    """
    Create a new resource document in Appwrite.
    Expected JSON body with fields: title, type, source, tags, difficulty_level, summary, access_level.
    """
    data = request.json or {}
    # For example:
    # {
    #   "title": "Python Basics",
    #   "type": "VIDEO",
    #   "source": "YOUTUBE",
    #   "tags": ["python", "basics", "programming"],
    #   "difficulty_level": "BEGINNER",
    #   "summary": "An introduction to Python",
    #   "access_level": "FREE"
    # }
    
    client = create_appwrite_client()
    databases = Databases(client)

    try:
        # Create the resource document
        new_doc = databases.create_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_RESOURCES_COLLECTION_ID,
            document_id=ID.unique(),
            data={
                "title": data.get("title", ""),
                "type": data.get("type", ""),
                "source": data.get("source", ""),
                "tags": data.get("tags", []),
                "difficulty_level": data.get("difficulty_level", ""),
                "summary": data.get("summary", ""),
                "access_level": data.get("access_level", ""),
                "upvotes": 0,
                "downvotes": 0,
                "community": data.get("community",""),
            }
        )
        
        return jsonify(new_doc), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route('/', methods=['GET'])
def get_all_resources():
    """
    Fetch all resource documents from the Appwrite Resources collection.
    """
    client = create_appwrite_client()
    databases = Databases(client)

    try:
        result = databases.list_documents(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_RESOURCES_COLLECTION_ID,
        )
        # result typically looks like { 'total': X, 'documents': [...] }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route('/<resource_id>', methods=['GET'])
def get_resource(resource_id):
    """
    Fetch a single resource by its ID.
    """
    client = create_appwrite_client()
    databases = Databases(client)

    try:
        doc = databases.get_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_RESOURCES_COLLECTION_ID,
            document_id=resource_id
        )
        return jsonify(doc), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@resources_bp.route('/<resource_id>', methods=['PUT'])
def update_resource(resource_id):
    """
    Update an existing resource document by its ID.
    Expected JSON body with any of the resource fields.
    """
    data = request.json or {}
    
    client = create_appwrite_client()
    databases = Databases(client)

    try:
        updated_doc = databases.update_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_RESOURCES_COLLECTION_ID,
            document_id=resource_id,
            data={
                "title": data.get("title", ""),
                "type": data.get("type", ""),
                "source": data.get("source", ""),
                "tags": data.get("tags", []),
                "difficulty_level": data.get("difficulty_level", ""),
                "summary": data.get("summary", ""),
                "access_level": data.get("access_level", "")
            }
        )
        return jsonify(updated_doc), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route('/<resource_id>', methods=['DELETE'])
def delete_resource(resource_id):
    """
    Delete a resource document by its ID.
    """
    client = create_appwrite_client()
    databases = Databases(client)

    try:
        databases.delete_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_RESOURCES_COLLECTION_ID,
            document_id=resource_id
        )
        return jsonify({"success": True, "message": "Resource deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

