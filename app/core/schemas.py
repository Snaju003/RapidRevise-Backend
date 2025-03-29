from pydantic import BaseModel, Field
from typing import Dict, List, Union


class YoutubeParams(BaseModel):
    query: str
    maxResults: int = Field(default=5)
    filters: Dict[str, Union[float, int]] = Field(default_factory=lambda: {
        "minRating": 0.5,
        "maxDuration": 30
    })


class ArticleParams(BaseModel):
    query: str
    maxResults: int = Field(default=3)
    prioritize: List[str] = Field(default_factory=lambda: [
                                  "academic", "tutorials", "blogs"])


class FreeResourceParams(BaseModel):
    query: str
    maxResults: int = Field(default=3)
    types: List[str] = Field(default_factory=lambda: [
                             "practice_tests", "cheatsheets", "summaries"])


class Resources(BaseModel):
    youtube: YoutubeParams
    articles: ArticleParams
    free_resources: FreeResourceParams


class LearningResourceParameters(BaseModel):
    subjects: List[str]
    exam_priority_topics: List[str] = Field(default_factory=list)
    total_study_time: int
    resources: Resources
