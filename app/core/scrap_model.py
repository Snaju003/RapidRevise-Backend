import json
import logging
from groq import Groq
from app.core.schemas import ArticleParams, FreeResourceParams, LearningResourceParameters, Resources, YoutubeParams
from app.core.youtube_scrap import StudyPlanGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq = Groq(api_key="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")

SYSTEM_PROMPT = """
You are an AI Study Plan Optimizer specializing in efficient exam preparation. For any learning request:
1. Identify the subject and available study time
2. Generate optimized search queries based on time constraints:
   - Short time (≤3 hours): Focus exclusively on highest-priority exam topics and quick review materials
   - Medium time (4-8 hours): Cover core exam topics with selected important concepts
   - Extended time (>8 hours): Provide comprehensive coverage including theory, models, and applications
3. For each identified subject, determine 3-5 essential subtopics that are most frequently tested in exams
4. Prioritize resources with high educational value (lectures from reputable institutions, exam-focused reviews)
5. Filter out introductory/basic content for intermediate/advanced subjects
6. Include practice questions/exercises when available to reinforce learning
7. Adapt detail level and scope based on urgency implied in the request

The JSON output must follow this exact schema:
{
  "subjects": [<subject strings>],
  "exam_priority_topics": [<list of 3-5 most critical topics for passing exams>],
  "total_study_time": <study time in hours>,
  "resources": {
    "youtube": {"query": <optimized search query string>, "maxResults": <integer>, "filters": {"minRating": <float>, "maxDuration": <minutes>}},
  }
}
"""


class ScrapModel:
    def __init__(self):
        self.groq = Groq(
            api_key="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")
        SYSTEM_PROMPT="""
        """
