from app.utils.appwrite import get_database_service
from flask import current_app

class User:
    """
    User model for interacting with Appwrite user collection
    """
    
    @staticmethod
    def get_by_id(user_id):
        """
        Get user by ID
        """
        database_service = get_database_service()
        
        try:
            user_doc = database_service.get_document(
                database_id=current_app.config['APPWRITE_DATABASE_ID'],
                collection_id=current_app.config['APPWRITE_USER_COLLECTION_ID'],
                document_id=user_id
            )
            return user_doc
        except Exception as e:
            print(f"Error fetching user: {str(e)}")
            return None
    
    @staticmethod
    def get_by_email(email):
        """
        Get user by email
        """
        database_service = get_database_service()
        
        try:
            users = database_service.list_documents(
                database_id=current_app.config['APPWRITE_DATABASE_ID'],
                collection_id=current_app.config['APPWRITE_USER_COLLECTION_ID'],
                queries=[f'email={email}']
            )
            
            if users.get('total', 0) > 0:
                return users.get('documents')[0]
            return None
        except Exception as e:
            print(f"Error fetching user by email: {str(e)}")
            return None