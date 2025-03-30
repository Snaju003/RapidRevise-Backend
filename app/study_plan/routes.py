from fileinput import filename
import os
from flask import request, jsonify
from werkzeug.utils import secure_filename
from app.core.pdf_file_reader import RagService
from app.study_plan import bp
from app.services import create_appwrite_client
from appwrite.services.databases import Databases
from appwrite.id import ID
from appwrite.query import Query
from config import Config

@bp.route('/', methods=['POST'])
def create_study_plan():
    """
    Create a new study plan in Personal_Resources, 
    plus child documents in StudyPlan, TopicsWithVideos, and Video.
    """
    data = request.json or {}
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    client = create_appwrite_client()
    databases = Databases(client)
    
    try:
        # 1. Create the parent 'Personal_Resources' document
        #    (Adjust 'type' and 'source' as needed for your enum)
        personal_resources_doc = databases.create_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_PERSONAL_RESOURCES_COLLECTION_ID,
            document_id=ID.unique(),
            data={
                "type": data.get("type", "VIDEO"),      # or "STUDY", etc. if your enum differs
                "source": data.get("source", "YOUTUBE"),
                # If you want to store an overall label or any additional fields, add them here.
            }
        )
        
        personal_resources_id = personal_resources_doc["$id"]
        
        # 2. Create documents in the StudyPlan collection (question + recommendation)
        #    referencing the newly created personal resource document.
        for item in data.get("study_plan", []):
            databases.create_document(
                database_id=Config.APPWRITE_DATABASE_ID,
                collection_id=Config.APPWRITE_STUDY_PLAN_COLLECTION_ID,  # adjust if different
                document_id=ID.unique(),
                data={
                    "question": item.get("question"),
                    "recommendation": item.get("recommendation"),
                    # This links each study plan item to the parent personal resource
                    "personalResources": personal_resources_id
                }
            )
        
        # 3. Create 'topics_with_videos' and corresponding 'video' documents.
        #    Each topic references the personal resource; each video references the topic.
        for topic_data in data.get("topics_with_videos", []):
            # Create the topic document
            topic_doc = databases.create_document(
                database_id=Config.APPWRITE_DATABASE_ID,
                collection_id=Config.APPWRITE_TOPICS_WITH_VIDEOS_COLLECTION_ID,
                document_id=ID.unique(),
                data={
                    "importance": topic_data.get("importance"),
                    "prep_time_minutes": topic_data.get("prep_time_minutes"),
                    "topic_name": topic_data.get("topic_name"),
                    # This links the topic doc to the parent personal resource
                    "personalResources": personal_resources_id
                }
            )
            
            topic_id = topic_doc["$id"]
            
            # Create each video document linked to the topic
            for video_data in topic_data.get("videos", []):
                databases.create_document(
                    database_id=Config.APPWRITE_DATABASE_ID,
                    collection_id=Config.APPWRITE_VIDEO_COLLECTION_ID,
                    document_id=ID.unique(),
                    data={
                        "channel": video_data.get("channel"),
                        "duration": video_data.get("duration"),
                        "thumbnail": video_data.get("thumbnail"),
                        "title": video_data.get("title"),
                        "url": video_data.get("url"),
                        "video_id": video_data.get("video_id"),
                        "views": video_data.get("views"),
                        # Link back to the topic
                        "topicsWithVideos": topic_id
                    }
                )
        
        return jsonify(personal_resources_doc), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@bp.route('/', methods=['GET'])
def get_all_study_plans():
    """
    Get all study plans with their topics and videos.
    """
    client = create_appwrite_client()
    databases = Databases(client)
    
    try:
        # Get all study plans
        study_plans = databases.list_documents(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_PERSONAL_RESOURCES_COLLECTION_ID,
            queries=[
                Query.equal("type", "VIDEO")
            ]
        )
        
        result = []
        
        for plan in study_plans.get('documents', []):
            # Get topics for this study plan
            topics = databases.list_documents(
                database_id=Config.APPWRITE_DATABASE_ID,
                collection_id=Config.APPWRITE_TOPICS_WITH_VIDEOS_COLLECTION_ID,
                queries=[
                    Query.equal("personalResources", plan['$id'])
                ]
            )
            
            plan_data = {
                'id': plan['$id'],
                'study_plan': plan.get('study_plan', ''),
                'topics_with_videos': []
            }
            
            for topic in topics.get('documents', []):
                # Get videos for this topic
                videos = databases.list_documents(
                    database_id=Config.APPWRITE_DATABASE_ID,
                    collection_id=Config.APPWRITE_VIDEO_COLLECTION_ID,
                    queries=[
                        Query.equal("topicsWithVideos", topic['$id'])
                    ]
                )
                
                topic_data = {
                    'id': topic['$id'],
                    'importance': topic.get('importance'),
                    'prep_time_minutes': topic.get('prep_time_minutes'),
                    'topic_name': topic.get('topic_name'),
                    'videos': []
                }
                
                for video in videos.get('documents', []):
                    video_data = {
                        'id': video['$id'],
                        'channel': video.get('channel'),
                        'duration': video.get('duration'),
                        'thumbnail': video.get('thumbnail'),
                        'title': video.get('title'),
                        'url': video.get('url'),
                        'video_id': video.get('video_id'),
                        'views': video.get('views')
                    }
                    topic_data['videos'].append(video_data)
                
                plan_data['topics_with_videos'].append(topic_data)
            
            result.append(plan_data)    
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/<string:id>', methods=['GET'])
def get_study_plan(id):
    """
    Get a specific study plan with its topics and videos.
    """
    client = create_appwrite_client()
    databases = Databases(client)
    
    try:
        # Get the study plan
        plan = databases.get_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_PERSONAL_RESOURCES_COLLECTION_ID,
            document_id=id
        )
        
        # Get topics for this study plan
        topics = databases.list_documents(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_TOPICS_WITH_VIDEOS_COLLECTION_ID,
            queries=[
                Query.equal("personalResources", id)
            ]
        )
        
        plan_data = {
            'id': plan['$id'],
            'study_plan': plan.get('study_plan', ''),
            'topics_with_videos': []
        }
        
        for topic in topics.get('documents', []):
            # Get videos for this topic
            videos = databases.list_documents(
                database_id=Config.APPWRITE_DATABASE_ID,
                collection_id=Config.APPWRITE_VIDEO_COLLECTION_ID,
                queries=[
                    Query.equal("topicsWithVideos", topic['$id'])
                ]
            )
            
            topic_data = {
                'id': topic['$id'],
                'importance': topic.get('importance'),
                'prep_time_minutes': topic.get('prep_time_minutes'),
                'topic_name': topic.get('topic_name'),
                'videos': []
            }
            
            for video in videos.get('documents', []):
                video_data = {
                    'id': video['$id'],
                    'channel': video.get('channel'),
                    'duration': video.get('duration'),
                    'thumbnail': video.get('thumbnail'),
                    'title': video.get('title'),
                    'url': video.get('url'),
                    'video_id': video.get('video_id'),
                    'views': video.get('views')
                }
                topic_data['videos'].append(video_data)
            
            plan_data['topics_with_videos'].append(topic_data)
        
        return jsonify(plan_data)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/topicWithVideos_relationships/<string:study_plan_id>', methods=['GET'])
def get_study_plan_relationships(study_plan_id):
    """
    Get the relationship IDs between a study plan and its topics.
    """
    client = create_appwrite_client()
    databases = Databases(client)
    
    try:
        # Get the study plan
        study_plan = databases.get_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_PERSONAL_RESOURCES_COLLECTION_ID,
            document_id=study_plan_id
        )
        
        # Get topics linked to this study plan
        topics = databases.list_documents(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_TOPICS_WITH_VIDEOS_COLLECTION_ID,
            queries=[
                Query.equal("personalResources", study_plan_id)
            ]
        )
        
        # Format the result showing the relationship
        result = {
            "study_plan": {
                "id": study_plan["$id"],
                "type": study_plan.get("type"),
                "source": study_plan.get("source")
            },
            "topics": [
                {
                    "id": topic["$id"],
                    "name": topic.get("topic_name"),
                    "importance": topic.get("importance")
                } for topic in topics.get("documents", [])
            ]
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/studyplan_relationships/<string:study_plan_id>', methods=['GET'])
def get_study_plan_items_relationships(study_plan_id):
    """
    Get the relationship IDs between a study plan (Personal Resources document)
    and its study plan items (the question and recommendation pairs).
    """
    client = create_appwrite_client()
    databases = Databases(client)
    
    try:
        # Retrieve the parent study plan document from Personal Resources
        study_plan = databases.get_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_PERSONAL_RESOURCES_COLLECTION_ID,
            document_id=study_plan_id
        )
        
        # Retrieve all study plan items linked to the parent document
        study_plan_items = databases.list_documents(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_STUDY_PLAN_COLLECTION_ID,
            queries=[
                Query.equal("personalResources", study_plan_id)
            ]
        )
        
        # Format the result to show the parent study plan details and the list of study plan items
        result = {
            "study_plan": {
                "id": study_plan["$id"],
                "type": study_plan.get("type"),
                "source": study_plan.get("source")
            },
            "studyPlanItems": [
                {
                    "id": item["$id"],
                    "question": item.get("question"),
                    "recommendation": item.get("recommendation")
                } for item in study_plan_items.get("documents", [])
            ]
        }
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/<string:id>', methods=['DELETE'])
def delete_study_plan(id):
    """
    Delete a study plan and its related topics and videos.
    """
    client = create_appwrite_client()
    databases = Databases(client)
    
    try:
        # Get topics for this study plan first
        topics = databases.list_documents(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_TOPICS_WITH_VIDEOS_COLLECTION_ID,
            queries=[
                Query.equal("personalResources", id)
            ]
        )
        
        # Delete videos for each topic
        for topic in topics.get('documents', []):
            topic_id = topic['$id']
            
            videos = databases.list_documents(
                database_id=Config.APPWRITE_DATABASE_ID,
                collection_id=Config.APPWRITE_VIDEO_COLLECTION_ID,
                queries=[
                    Query.equal("topicsWithVideos", topic_id)
                ]
            )
            
            for video in videos.get('documents', []):
                databases.delete_document(
                    database_id=Config.APPWRITE_DATABASE_ID,
                    collection_id=Config.APPWRITE_VIDEO_COLLECTION_ID,
                    document_id=video['$id']
                )
            
            # Delete the topic
            databases.delete_document(
                database_id=Config.APPWRITE_DATABASE_ID,
                collection_id=Config.APPWRITE_TOPICS_WITH_VIDEOS_COLLECTION_ID,
                document_id=topic_id
            )
        
        # Delete the study plan
        databases.delete_document(
            database_id=Config.APPWRITE_DATABASE_ID,
            collection_id=Config.APPWRITE_PERSONAL_RESOURCES_COLLECTION_ID,
            document_id=id
        )
        
        return jsonify({"message": "Study plan deleted successfully"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@bp.route('/pdf', methods=['POST'])
def upload_pdf():
    """
    Upload a PDF file to the server.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Check if the file is a PDF
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Invalid file type. Please upload a PDF file."}), 400

    # Secure the filename and create the directory if it doesn't exist
    filename = secure_filename(file.filename)
    directory = 'data'
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, filename)

    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

    # Initialize RagService with the PDF file
    try:
        rag_service = RagService()
        rag_service.initialize(file_path)
        print("Initialized")
    except Exception as e:
        return jsonify({"error": f"Failed to initialize RagService: {str(e)}"}), 500

    # Retrieve the prompt.
    # First, try to get it from JSON if available.
    prompt = None
    if request.is_json:
        prompt = request.json.get("prompt")
    # If not available in JSON, check the form data.
    if not prompt:
        prompt = request.form.get("prompt")
    if not prompt:
        return jsonify({"error": "Prompt not provided."}), 400

    try:
        context = rag_service.get_context(prompt)
        res = rag_service.generate_response(prompt, context)
    except Exception as e:
        return jsonify({"error": f"Error processing prompt: {str(e)}"}), 500

    return jsonify({'message': str(res)}), 200
