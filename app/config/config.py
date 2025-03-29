import os


class Config:
    def __init__(self):
        self.YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
        self.APPWRITE_API_KEY = os.environ.get("APPWRITE_API_KEY")
        self.APPWRITE_ENDPOINT = os.environ.get("APPWRITE_ENDPOINT")
        self.APPWRITE_PROJECT_ID = os.environ.get("APPWRITE_PROJECT_ID")
        self.APPWRITE_DB = os.environ.get("APPWRITE_DB")
        self.USER_COLLECTION_ID = os.environ.get("USER_COLLECTION_ID")
        self.COMMUNITY_COLLECTION_ID = os.environ.get(
            "COMMUNITY_COLLECTION_ID")
        self.RESOURCES_COLLECTION_ID = os.environ.get(
            "RESOURCES_COLLECTION_ID")

    def getYoutubeApiKey(self):
        return self.YOUTUBE_API_KEY
