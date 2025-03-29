import httplib2
from typing import Dict, List
import concurrent
from googleapiclient.discovery import build
import re
from concurrent.futures import ThreadPoolExecutor
import logging
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer


class StudyPlanGenerator:
    def __init__(self, youtube_api_key: str, subjects: List[str], exam_priority_topics: List[str], total_study_time: int, resources: Dict):
        self.subjects = subjects
        self.exam_priority_topics = exam_priority_topics
        self.total_study_time = total_study_time
        self.resources = resources
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing StudyPlanGenerator")
        try:
            self.logger.info("Initializing YouTube API client")
            http_client = httplib2.Http()
            self.youtube = build('youtube', 'v3', developerKey=youtube_api_key,
                                 http=http_client, cache_discovery=False, static_discovery=False)
            self.logger.info("YouTube API client initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing YouTube API client: {e}")
            self.youtube = None
        try:
            self.logger.info("Initializing NLTK components")
            resources_to_check = {
                'punkt': 'tokenizers/punkt',
                'stopwords': 'corpora/stopwords',
                'wordnet': 'corpora/wordnet'
            }
            for package, path in resources_to_check.items():
                try:
                    nltk.data.find(path)
                    self.logger.info(f"NLTK {package} already downloaded")
                except LookupError:
                    self.logger.info(f"Downloading NLTK {package}")
                    nltk.download(package, quiet=True)
            self.stop_words = set(stopwords.words('english'))
            self.lemmatizer = WordNetLemmatizer()
            self.logger.info("NLTK components initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing NLTK components: {e}")
            self.stop_words = set()
            self.lemmatizer = lambda w: w
        self.logger.info("StudyPlanGenerator initialization completed")

    def fetch_educational_videos(self) -> List[Dict]:
        """Fetch educational videos from YouTube based on the configured parameters."""
        try:
            yt_query = f"{' '.join(self.subjects)} {' '.join(self.exam_priority_topics[:2])} tutorial"
            if hasattr(self.resources.youtube, 'query'):
                yt_query = self.resources.youtube.query

            max_results = self.resources.youtube.maxResults
            filters = self.resources.youtube.filters

            self.logger.info(f"Fetching YouTube videos with query: {yt_query}")

            # Adjust search parameters based on study time
            relevance_language = 'en'
            video_duration = 'medium' if self.total_study_time < 4 else 'any'

            search_response = self.youtube.search().list(
                q=yt_query,
                type='video',
                part='id,snippet',
                maxResults=max_results * 2,  # Fetch more than needed to allow for filtering
                relevanceLanguage=relevance_language,
                videoEmbeddable='true',
                videoDuration=video_duration
            ).execute()

            video_ids = [item['id']['videoId']
                         for item in search_response.get('items', [])]

            if not video_ids:
                self.logger.warning("No videos found for the given query")
                return []

            # Get detailed information about each video
            video_details = self.youtube.videos().list(
                part='contentDetails,statistics,snippet',
                id=','.join(video_ids)
            ).execute()
            
            videos = []
            for item in video_details.get('items', []):
                duration_minutes = self._parse_duration(
                    item['contentDetails']['duration'])

                # Apply duration filter
                if filters.get('maxDuration') and duration_minutes > filters.get('maxDuration'):
                    continue

                like_count = int(item['statistics'].get('likeCount', 0))
                view_count = int(item['statistics'].get('viewCount', 0))

                # Calculate engagement score
                if view_count > 0:
                    engagement_score = (like_count / view_count) * 100
                else:
                    engagement_score = 0

                # Apply engagement filter
                if filters.get('minRating') and engagement_score < filters.get('minRating'):
                    continue

                # Get video URL
                video_url = f"https://www.youtube.com/watch?v={item['id']}"

                # Calculate priority match using NLP
                priority_match = self._calculate_priority_match_nlp(
                    item['snippet']['title'],
                    item['snippet']['description']
                )

                videos.append({
                    'id': item['id'],
                    'title': item['snippet']['title'],
                    'channel': item['snippet']['channelTitle'],
                    'description': item['snippet']['description'][:150] + "..." if len(item['snippet']['description']) > 150 else item['snippet']['description'],
                    'url': video_url,
                    'duration_minutes': duration_minutes,
                    'views': view_count,
                    'engagement_score': round(engagement_score, 2),
                    'publishedAt': item['snippet']['publishedAt'],
                    'thumbnail': item['snippet']['thumbnails']['high']['url'],
                    'priority_match': priority_match
                })

            # Sort by priority match first, then by engagement score
            return sorted(videos, key=lambda x: (x['priority_match'], x['engagement_score']), reverse=True)[:max_results]

        except Exception as e:
            self.logger.error(f"Error fetching videos: {str(e)}")
            return []

    def _calculate_priority_match(self, title: str, description: str) -> int:
        """Basic priority matching based on keyword presence."""
        combined_text = (title + " " + description).lower()
        return sum(1 for topic in self.exam_priority_topics if topic.lower() in combined_text)

    def _calculate_priority_match_nlp(self, title: str, description: str) -> float:
        """Enhanced priority matching using NLP techniques."""
        # Basic match score
        basic_score = self._calculate_priority_match(title, description)

        # Preprocess the content text
        combined_text = (title + " " + description).lower()
        words = word_tokenize(combined_text)
        words = [self.lemmatizer.lemmatize(
            w) for w in words if w.isalnum() and w not in self.stop_words]

        # Calculate semantic similarity with priority topics
        topic_words = []
        for topic in self.exam_priority_topics:
            topic_tokens = word_tokenize(topic.lower())
            topic_words.extend([self.lemmatizer.lemmatize(w) for w in topic_tokens
                               if w.isalnum() and w not in self.stop_words])

        # Calculate word overlap
        overlap = sum(1 for word in words if word in topic_words)

        # Combine scores (basic match has higher weight)
        return basic_score * 2 + overlap * 0.5

    def fetch_articles(self) -> List[Dict]:
        """Fetch educational articles from various sources."""
        try:
            max_results = self.resources.articles.maxResults
            prioritize = self.resources.articles.prioritize if hasattr(
                self.resources.articles, 'prioritize') else ["academic", "tutorials", "blogs"]
            query = self.resources.articles.query

            articles = []
            for source_type in prioritize:
                if source_type == "academic":
                    new_articles = self._fetch_academic_articles(query)
                elif source_type == "tutorials":
                    new_articles = self._fetch_tutorial_articles(query)
                else:
                    new_articles = self._fetch_general_articles(query)

                articles.extend(new_articles)
                if len(articles) >= max_results:
                    break

            return articles[:max_results]

        except Exception as e:
            self.logger.error(f"Error fetching articles: {str(e)}")
            return []

    def _fetch_academic_articles(self, query: str) -> List[Dict]:
        """Fetch academic articles. This would ideally connect to academic databases."""
        # This would be replaced with actual API calls in production
        return [{
            'title': f"Academic article on {topic}",
            'url': f"https://example.com/academic-{topic.replace(' ', '-')}",
            'source': "Academic Source",
            'summary': f"Academic article covering {topic} for exam preparation.",
            'estimated_reading_time': 15
        } for topic in self.exam_priority_topics[:2]]

    def _fetch_tutorial_articles(self, query: str) -> List[Dict]:
        """Fetch tutorial articles from educational websites."""
        # This would be replaced with actual web scraping in production
        return [{
            'title': f"Tutorial on {topic}",
            'url': f"https://example.com/tutorial-{topic.replace(' ', '-')}",
            'source': "Tutorial site",
            'summary': f"Step-by-step tutorial covering {topic} for exam preparation.",
            'estimated_reading_time': 10
        } for topic in self.exam_priority_topics[:2]]

    def _fetch_general_articles(self, query: str) -> List[Dict]:
        """Fetch general educational articles from blogs and websites."""
        # This would be replaced with actual web scraping in production
        return [{
            'title': f"Guide to {self.subjects[0]}",
            'url': "https://example.com/guide",
            'source': "Educational blog",
            'summary': "Comprehensive guide covering essential exam topics.",
            'estimated_reading_time': 8
        }]

    def fetch_free_resources(self) -> List[Dict]:
        """Fetch free educational resources like practice tests and cheatsheets."""
        try:
            resource_types = self.resources.free_resources.types if hasattr(
                self.resources.free_resources, 'types') else ["practice_tests", "cheatsheets", "summaries"]
            max_results = self.resources.free_resources.maxResults

            resources = []
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_type = {
                    executor.submit(self._fetch_resource_by_type, r_type): r_type
                    for r_type in resource_types
                }

                for future in concurrent.futures.as_completed(future_to_type):
                    resources.extend(future.result())

            return resources[:max_results]

        except Exception as e:
            self.logger.error(f"Error fetching free resources: {str(e)}")
            return []

    def _fetch_resource_by_type(self, resource_type: str) -> List[Dict]:
        """Fetch resources by type (practice tests, cheatsheets, etc.)."""
        # This would be replaced with actual API calls or web scraping in production
        if resource_type == "practice_tests":
            return [{
                'title': f"Practice Test for {topic}",
                'url': f"https://example.com/test-{topic.replace(' ', '-')}",
                'type': "Practice Test",
                'description': f"Exam-style questions focused on {topic}.",
                'estimated_time': 20
            } for topic in self.exam_priority_topics[:1]]
        elif resource_type == "cheatsheets":
            return [{
                'title': f"Cheatsheet for {self.subjects[0]}",
                'url': f"https://example.com/cheatsheet-{self.subjects[0].replace(' ', '-')}",
                'type': "Cheatsheet",
                'description': "Quick reference guide with key formulas and concepts.",
                'estimated_time': 5
            }]
        else:
            return [{
                'title': f"Study Summary for {self.subjects[0]}",
                'url': f"https://example.com/summary-{self.subjects[0].replace(' ', '-')}",
                'type': resource_type,
                'description': f"Concise summary of key concepts in {self.subjects[0]}.",
                'estimated_time': 10
            }]

    def _parse_duration(self, duration: str) -> int:
        """Parse ISO 8601 duration format to minutes."""
        pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
        match = pattern.match(duration)
        if not match:
            return 0
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        seconds = int(match.group(3)) if match.group(3) else 0
        return hours * 60 + minutes + seconds // 60

    def _allocate_study_time(self) -> Dict[str, int]:
        """Dynamically allocate study time based on total available time and topic complexity."""
        available_minutes = self.total_study_time * 60
        time_allocation = {}

        # Adjust allocation based on available time
        if self.total_study_time <= 3:
            # Very short time: Focus on videos and quick practice
            time_allocation = {
                'videos': 0.6,
                'practice': 0.3,
                'reading': 0.1
            }
        elif self.total_study_time <= 8:
            # Medium time: Balanced approach
            time_allocation = {
                'videos': 0.5,
                'practice': 0.25,
                'reading': 0.25
            }
        else:
            # Extended time: More thorough learning with practice and reading
            time_allocation = {
                'videos': 0.4,
                'practice': 0.3,
                'reading': 0.3
            }

        # Convert percentages to minutes
        return {
            'video_time': int(available_minutes * time_allocation['videos']),
            'practice_time': int(available_minutes * time_allocation['practice']),
            'reading_time': int(available_minutes * time_allocation['reading'])
        }

    def generate_study_plan(self) -> Dict:
        """Generate a comprehensive study plan based on available resources and time."""
        try:
            # Fetch all needed resources
            videos = self.fetch_educational_videos()
            # articles = self.fetch_articles()
            # free_resources = self.fetch_free_resources()

            # Allocate study time
            time_allocation = self._allocate_study_time()

            # Select videos that fit within allocated time
            video_time_available = time_allocation['video_time']
            selected_videos = []
            total_video_time = 0

            for video in videos:
                if total_video_time + video['duration_minutes'] <= video_time_available:
                    selected_videos.append(video)
                    total_video_time += video['duration_minutes']

            # Calculate reading time for articles
            # estimated_reading_time = sum(
            #     article.get('estimated_reading_time', len(
            #         article.get('summary', '')) // 200 * 5)
            #     for article in articles
            # )

            # Calculate practice time
            # estimated_practice_time = sum(
            #     resource.get('estimated_time', 15)
            #     for resource in free_resources
            # )

            # Create the study plan
            study_plan = {
                'plan_summary': {
                    'subject': self.subjects[0],
                    'exam_priority_topics': self.exam_priority_topics,
                    'total_study_time_hours': self.total_study_time,
                    'time_allocation': {
                        'video_learning_minutes': total_video_time,
                        # 'reading_minutes': min(time_allocation['reading_time'], estimated_reading_time),
                        # 'practice_minutes': min(time_allocation['practice_time'], estimated_practice_time)
                    }
                },
                'learning_resources': {
                    'videos': selected_videos,
                    # 'articles': articles,
                    # 'practice_materials': free_resources
                },
                'study_sequence': self._generate_study_sequence(
                    selected_videos,
                    [], []
                    # articles,
                    # free_resources
                ),
                'remaining_time_minutes': (
                    video_time_available - total_video_time
                    # max(0, time_allocation['reading_time'] - estimated_reading_time) +
                    # max(0, time_allocation['practice_time'] -
                    #     estimated_practice_time)
                )
            }

            return study_plan

        except Exception as e:
            self.logger.error(f"Error generating study plan: {str(e)}")
            return {
                'error': f"Failed to generate study plan: {str(e)}",
                'plan_summary': {
                    'subject': self.subjects[0] if self.subjects else "Unknown",
                    'exam_priority_topics': self.exam_priority_topics,
                    'total_study_time_hours': self.total_study_time
                }
            }

    def _generate_study_sequence(self, videos, articles, resources) -> List[Dict]:
        """Generate a sequence of study activities based on available resources and time constraints."""
        sequence = []

        # Different sequencing strategies based on available time
        if self.total_study_time <= 3:
            # Short study time: Focus on high-priority content

            # Start with a quick overview if available
            if articles and len(articles) > 0:
                sequence.append({
                    'step': len(sequence) + 1,
                    'activity': f"Quick Read: {articles[0]['title']}",
                    'duration_minutes': articles[0].get('estimated_reading_time', 10),
                    'resource_type': 'article',
                    'resource_url': articles[0]['url']
                })

            # Add highest priority videos
            for video in videos[:min(2, len(videos))]:
                sequence.append({
                    'step': len(sequence) + 1,
                    'activity': f"Watch: {video['title']}",
                    'duration_minutes': video['duration_minutes'],
                    'resource_type': 'video',
                    'resource_url': video['url']
                })

            # Add a quick reference resource
            if resources and len(resources) > 0:
                sequence.append({
                    'step': len(sequence) + 1,
                    'activity': f"Review: {resources[0]['title']}",
                    'duration_minutes': resources[0].get('estimated_time', 15),
                    'resource_type': 'reference',
                    'resource_url': resources[0]['url']
                })

            # Add remaining videos if time permits
            for video in videos[min(2, len(videos)):]:
                sequence.append({
                    'step': len(sequence) + 1,
                    'activity': f"Watch: {video['title']}",
                    'duration_minutes': video['duration_minutes'],
                    'resource_type': 'video',
                    'resource_url': video['url']
                })

        elif self.total_study_time <= 8:
            # Medium study time: Balanced approach

            # Start with an overview article
            if articles and len(articles) > 0:
                sequence.append({
                    'step': len(sequence) + 1,
                    'activity': f"Read: {articles[0]['title']}",
                    'duration_minutes': articles[0].get('estimated_reading_time', 15),
                    'resource_type': 'article',
                    'resource_url': articles[0]['url']
                })

            # Interleave videos and practice
            video_index = 0
            resource_index = 0
            article_index = 1  # Skip the first article which we already added

            while video_index < len(videos):
                # Add a video
                if video_index < len(videos):
                    sequence.append({
                        'step': len(sequence) + 1,
                        'activity': f"Watch: {videos[video_index]['title']}",
                        'duration_minutes': videos[video_index]['duration_minutes'],
                        'resource_type': 'video',
                        'resource_url': videos[video_index]['url']
                    })
                    video_index += 1

                # Add a practice resource after every other video
                if video_index % 2 == 0 and resource_index < len(resources):
                    sequence.append({
                        'step': len(sequence) + 1,
                        'activity': f"Practice: {resources[resource_index]['title']}",
                        'duration_minutes': resources[resource_index].get('estimated_time', 15),
                        'resource_type': 'practice',
                        'resource_url': resources[resource_index]['url']
                    })
                    resource_index += 1

                # Add another article after every 3 videos
                if video_index % 3 == 0 and article_index < len(articles):
                    sequence.append({
                        'step': len(sequence) + 1,
                        'activity': f"Read: {articles[article_index]['title']}",
                        'duration_minutes': articles[article_index].get('estimated_reading_time', 15),
                        'resource_type': 'article',
                        'resource_url': articles[article_index]['url']
                    })
                    article_index += 1

        else:
            # Extended study time: Comprehensive approach

            # Start with an introduction to the subject
            sequence.append({
                'step': len(sequence) + 1,
                'activity': f"Introduction to {self.subjects[0]}",
                'duration_minutes': 15,
                'resource_type': 'planning',
                'description': f"Review your study goals and familiarize yourself with the key topics in {self.subjects[0]}"
            })

            # Add initial context reading
            if articles and len(articles) > 0:
                sequence.append({
                    'step': len(sequence) + 1,
                    'activity': f"Read: {articles[0]['title']}",
                    'duration_minutes': articles[0].get('estimated_reading_time', 20),
                    'resource_type': 'article',
                    'resource_url': articles[0]['url']
                })

            # Create learning modules for each priority topic
            for i, topic in enumerate(self.exam_priority_topics):
                # Add module header
                sequence.append({
                    'step': len(sequence) + 1,
                    'activity': f"Module {i+1}: {topic}",
                    'duration_minutes': 5,
                    'resource_type': 'planning',
                    'description': f"Overview of key concepts in {topic}"
                })

                # Find videos relevant to this topic
                topic_videos = [v for v in videos if topic.lower() in v['title'].lower()
                                or topic.lower() in v['description'].lower()]

                # Use at least one video per topic
                if topic_videos:
                    for tv in topic_videos[:2]:  # Limit to 2 videos per topic
                        sequence.append({
                            'step': len(sequence) + 1,
                            'activity': f"Watch: {tv['title']}",
                            'duration_minutes': tv['duration_minutes'],
                            'resource_type': 'video',
                            'resource_url': tv['url']
                        })
                        # Remove this video from the main list to avoid duplication
                        if tv in videos:
                            videos.remove(tv)

                # Add relevant article if available
                topic_articles = [a for a in articles if topic.lower() in a['title'].lower()
                                  or topic.lower() in a.get('summary', '').lower()]
                if topic_articles:
                    sequence.append({
                        'step': len(sequence) + 1,
                        'activity': f"Read: {topic_articles[0]['title']}",
                        'duration_minutes': topic_articles[0].get('estimated_reading_time', 15),
                        'resource_type': 'article',
                        'resource_url': topic_articles[0]['url']
                    })

                # Add relevant practice if available
                topic_practice = [r for r in resources if topic.lower() in r['title'].lower()
                                  or topic.lower() in r.get('description', '').lower()]
                if topic_practice:
                    sequence.append({
                        'step': len(sequence) + 1,
                        'activity': f"Practice: {topic_practice[0]['title']}",
                        'duration_minutes': topic_practice[0].get('estimated_time', 20),
                        'resource_type': 'practice',
                        'resource_url': topic_practice[0]['url']
                    })

            # Add remaining videos
            for video in videos:
                sequence.append({
                    'step': len(sequence) + 1,
                    'activity': f"Watch: {video['title']}",
                    'duration_minutes': video['duration_minutes'],
                    'resource_type': 'video',
                    'resource_url': video['url']
                })

            # End with review and final practice
            sequence.append({
                'step': len(sequence) + 1,
                'activity': "Final Review",
                'duration_minutes': 30,
                'resource_type': 'review',
                'description': f"Summarize key concepts learned in {self.subjects[0]}"
            })

        return sequence
