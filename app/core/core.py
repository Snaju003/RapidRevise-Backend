import logging
import json
from typing import Dict, List, Any, Union
from groq import Groq
import os
from googleapiclient.discovery import build
import isodate
import re


class ExamPrepAgent:
    def __init__(self, groq_fetch_paper_api_key: str, groq_extract_topic_api_key: str, groq_gen_query_api_key: str, groq_struct_res_api_key: str, youtube_api_key: str):
        self.groq_fetch_paper = Groq(api_key=groq_fetch_paper_api_key)
        self.groq_extract_topic = Groq(api_key=groq_extract_topic_api_key)
        self.groq_gen_query = Groq(api_key=groq_gen_query_api_key)
        self.groq_struct_res = Groq(api_key=groq_struct_res_api_key)
        self.youtube_api_key = youtube_api_key
        self.youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        self.conversation_history = []
        self.logger = self._setup_logger()

        self.SYSTEM_PROMPT = """
            You are ExamPrepAI, a specialized educational agent designed to help students prepare for exams efficiently in limited time. 
            Your purpose is to analyze exam patterns, identify high-value topics, and recommend focused study resources.
            """

        self.type_prompts = {
            "FETCH_QUESTION_PAPER": """
                Based on the following educational context, describe in detail the types of question papers that would be relevant:
                - Educational Board/University: {board}
                - Class/Year Level: {class_level}
                - Department/Stream: {department}
                - Subject: {subject}
                Fetch the question papers for this topic. atleast 5.
                I don't need answer.. Only question
                Keep Subject name at top
            """,
            "ANALYZE_QUESTION_PAPER": """
                Extract ONLY the 5 most critical, high-value topics from these question papers:
                {paper}

                Provide your analysis as a structured list of EXACTLY 5 topics with their importance metrics.
                Focus only on topics relevant to {subject} for {board} {class_level} {department}.
    
                Return EXACTLY 5 most important topics for this specific subject based on your analysis.
                Do not include more than 5 topics under any circumstances.
            """,
            "GENERATE_QUERY": """
                Generate exactly ONE highly specific search query string for YouTube based on the topic: "{topic}" in {subject} for {board} {class_level} {department}.

                Create a single, focused query that will find the most relevant educational content.
                Return only the query string, nothing else.
            """,
            "RETURN_RESPONSE": """
                Organize the exam preparation materials into a structured response for the student.

                For each important topic (maximum 5):
                1. List the topic name and its importance score (1-10)
                2. Briefly explain why this topic is critical (e.g., "Appears in 80% of papers", "High mark allocation")
                3. Include 2-3 recommended YouTube videos with:
                - Title
                - Channel name
                - Duration
                - Direct link
                4. Add a brief note on how to approach studying this topic in limited time

                Structure this information in a clean, easy-to-navigate format that prioritizes the most critical topics first.
                Include a "Quick Study Plan" section at the end that suggests time allocation across all topics.

                The response should be comprehensive but focused on actionable information for last-minute preparation.
            """,
        }

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("ExamPrepAgent")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request through the agent workflow based on the request type."""
        try:
            request_type = request.get("type", "")
            self.logger.info(f"Processing request of type: {request_type}")

            if request_type == "FETCH_QUESTION_PAPER":
                return self._fetch_question_papers(request)
            elif request_type == "ANALYZE_QUESTION_PAPER":
                return self._analyze_question_papers(request)
            elif request_type == "GENERATE_QUERY":
                return self._generate_query(request)
            elif request_type == "RETURN_RESPONSE":
                return self._return_response(request)
            else:
                error_msg = f"Unknown request type: {request_type}"
                self.logger.error(error_msg)
                return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}

    def _call_llm(self, prompt: str, stage: str, temperature: float = 0.4) -> str:
        """Call the Fireworks LLM with the given prompt."""
        try:
            self.logger.info("Calling LLM with prompt")
            self.logger.info(f"_call_llm called with stage: {stage}")

            if stage == "FETCH_QUESTION_PAPER":
                chat_completion = self.groq_fetch_paper.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.2-90b-vision-preview",
                    temperature=temperature,
                    max_tokens=4096
                )
            elif stage == "ANALYZE_QUESTION_PAPER":
                chat_completion = self.groq_extract_topic.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.2-90b-vision-preview",
                    temperature=temperature,
                    max_tokens=4096
                )
            elif stage == "GENERATE_QUERY":
                chat_completion = self.groq_gen_query.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.2-90b-vision-preview",
                    temperature=temperature,
                    max_tokens=4096
                )
            elif stage == "RETURN_RESPONSE":
                chat_completion = self.groq_struct_res.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.2-90b-vision-preview",
                    temperature=temperature,
                    max_tokens=4096
                )
            else:
                error_msg = f"Unknown stage: {stage} {prompt}"
                self.logger.error(error_msg)
                return {"error": error_msg}

            response_content = chat_completion.choices[0].message.content
            self.logger.info("Received response from LLM")

            # Add to conversation history
            self.conversation_history.append({
                "prompt": prompt,
                "response": response_content
            })

            return response_content
        except Exception as e:
            error_msg = f"Error calling LLM: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def _fetch_question_papers(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch information about relevant question papers."""
        board = request.get("board", "")
        class_level = request.get("class_level", "")
        department = request.get("department", "")
        subject = request.get("subject", "")

        prompt = self.type_prompts["FETCH_QUESTION_PAPER"].format(
            board=board,
            class_level=class_level,
            department=department,
            subject=subject,
        )

        response = self._call_llm(prompt, stage="FETCH_QUESTION_PAPER")

        return {
            "status": "success",
            "papers_info": response,
            "metadata": {
                "board": board,
                "class_level": class_level,
                "department": department,
                "subject": subject
            }
        }

    def _analyze_question_papers(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the provided question papers to identify key topics."""
        papers = request.get("paper", "")
        subject = request.get("metadata", {}).get("subject", "")
        board = request.get("metadata", {}).get("board", "")
        class_level = request.get("metadata", {}).get("class_level", "")
        department = request.get("metadata", {}).get("department", "")

        # Update the prompt to focus on the specific subject and limit to 5 topics
        prompt = self.type_prompts["ANALYZE_QUESTION_PAPER"].format(
            paper=papers,
            subject=subject,
            board=board,
            class_level=class_level,
            department=department
        )

        response = self._call_llm(prompt, stage="ANALYZE_QUESTION_PAPER")

        # Parse the response to extract topics
        try:
            # Pass the subject to ensure topic extraction is focused
            topics = self._extract_topics(response, subject)
            
            # Ensure we only have 5 topics at most
            topics = topics[:5]
            
            return {
                "status": "success",
                "important_topics": topics,
                "raw_analysis": response,
                "metadata": {
                    "board": board,
                    "class_level": class_level,
                    "department": department,
                    "subject": subject
                }
            }
        except Exception as e:
            self.logger.error(f"Error extracting topics: {str(e)}")
            return {
                "status": "partial_success",
                "raw_analysis": response,
                "error": "Failed to structure topics data",
                "metadata": {
                    "board": board,
                    "class_level": class_level,
                    "department": department,
                    "subject": subject
                }
            }

    def _extract_topics(self, analysis_text: str, subject: str) -> List[Dict[str, Any]]:
        """Extract structured topic information from the LLM analysis."""
        # Include the subject in the structuring prompt and enforce the 5-topic limit
        structuring_prompt = f"""
        Based on your previous analysis, extract EXACTLY 5 important topics for {subject} in the following JSON format:
        [
            {{
                "topic_name": "Name of the topic specific to {subject}",
                "importance": 8,  // Scale of 1-10
                "prep_time_minutes": 60  // Estimated preparation time in minutes
            }},
            // More topics up to exactly 5 total
        ]
        
        Only respond with the valid JSON array with exactly 5 {subject} topics, nothing else.
        Do not include more than 5 topics.
        """

        structured_response = self._call_llm(
            prompt=structuring_prompt,
            temperature=0.7,
            stage="ANALYZE_QUESTION_PAPER"
        )

        # Try to extract just the JSON part
        try:
            # Find JSON in the response
            json_start = structured_response.find('[')
            json_end = structured_response.rfind(']') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = structured_response[json_start:json_end]
                topics = json.loads(json_str)
                # Double-check we're not exceeding 5 topics
                return topics[:5]
            else:
                # Fallback - try to parse the whole response
                topics = json.loads(structured_response)
                return topics[:5]
        except json.JSONDecodeError:
            # If we can't parse as JSON, return a simple structure
            self.logger.warning(
                "Failed to parse LLM output as JSON, creating simple structure")
            return [{"topic_name": f"Topic extraction failed for {subject}", "raw_analysis": structured_response}]

    def _generate_query(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimized search queries for different aspects of the given topic."""
        topic = request.get("topic", "")
        subject = request.get("metadata", {}).get("subject", "")
        board = request.get("metadata", {}).get("board", "")
        class_level = request.get("metadata", {}).get("class_level", "")
        department = request.get("metadata", {}).get("department", "")
        max_duration_minutes = request.get("max_duration_minutes", "180 Minutes")
        
        # Generate diverse aspect queries for the topic
        aspect_prompt = f"""
        Generate three different search queries for YouTube for the topic "{topic}" in {subject} for {board} {class_level} {department}.
        Each query should focus on a different aspect:
        1. Introduction or fundamentals of this topic
        2. Detailed explanation or applications of this topic
        3. Problem-solving or advanced concepts related to this topic
        
        For each, provide ONLY the query string itself, one per line. No numbering, no explanations.
        """
        
        aspect_response = self._call_llm(aspect_prompt, stage="GENERATE_QUERY", temperature=0.7)
        
        # Extract the three different queries
        aspect_queries = [query.strip() for query in aspect_response.strip().split('\n') if query.strip()]
        
        # Fallback to a default query if necessary
        if not aspect_queries:
            original_prompt = self.type_prompts["GENERATE_QUERY"].format(
                topic=topic,
                subject=subject,
                board=board,
                class_level=class_level,
                department=department
            )
            response = self._call_llm(original_prompt, stage="GENERATE_QUERY")
            aspect_queries = [self._extract_single_query(response)]
        
        # Limit to 3 queries max
        aspect_queries = aspect_queries[:3]
        
        # For each query, fetch candidate videos and accumulate them all
        all_videos = []
        for query in aspect_queries:
            candidate_videos = self._search_youtube_single(query, subject, max_duration_minutes)
            if candidate_videos:
                all_videos.extend(candidate_videos)
        
        # Remove duplicates based on video_id
        unique_videos = []
        video_ids = set()
        for video in all_videos:
            if video.get("video_id") and video["video_id"] not in video_ids:
                unique_videos.append(video)
                video_ids.add(video["video_id"])
        
        # Ensure we have at least 3 videos; if not, perform an additional broader search
        if len(unique_videos) < 3:
            fallback_query = f"{topic} {subject} lecture"
            additional_videos = self._search_youtube_single(fallback_query, subject, max_duration_minutes)
            for video in additional_videos:
                if video.get("video_id") and video["video_id"] not in video_ids:
                    unique_videos.append(video)
                    video_ids.add(video["video_id"])
                if len(unique_videos) >= 3:
                    break
        
        # Optionally, you can return exactly 3 videos or more if available.
        # Here we ensure a minimum of 3 videos per topic.
        return {
            "status": "success",
            "topic": topic,
            "search_queries": aspect_queries,
            "videos": unique_videos,  # This list will have at least 3 videos if available
            "metadata": {
                "board": board,
                "class_level": class_level,
                "department": department,
                "subject": subject
            }
        }


    def _extract_single_query(self, query_text: str) -> str:
        """Extract a single search query from the LLM response."""
        # Clean the response to get just the query
        query = query_text.strip()
        
        # Remove quotes if present
        if query.startswith('"') and query.endswith('"'):
            query = query[1:-1]
            
        # If there are multiple lines, take just the first substantial line
        if '\n' in query:
            lines = [line.strip() for line in query.split('\n') if line.strip()]
            if lines:
                query = lines[0]
                
        # Remove any numbering
        query = re.sub(r'^\d+\.\s*', '', query)
        
        return query

    def _search_youtube_single(self, query: str, subject: str, max_duration_minutes: int = None) -> List[Dict[str, Any]]:
        """
        Search YouTube for lectures on a topic.
        First, try to get one lecture whose title starts with 'Lec' or 'L'.
        Then, add the next two lectures from the same channel.
        """
        try:
            # Specific query targeting Gate Smashers
            specific_query = f"{query} {subject} Gate Smashers lecture"
            
            # Search for videos from Gate Smashers on this topic
            search_response = self.youtube.search().list(
                q=specific_query,
                part="snippet",
                maxResults=10,  # Request more to filter
                type="video"
            ).execute()
            
            candidate_videos = []
            # Process the search response and include channel_id in each candidate
            for item in search_response.get("items", []):
                channel_title = item["snippet"]["channelTitle"]
                # Check if this is from Gate Smashers (case-insensitive)
                if "gate smashers" not in channel_title.lower():
                    continue
                    
                video_id = item["id"]["videoId"]
                
                # Get video details to check duration and to extract channel_id
                video_response = self.youtube.videos().list(
                    part="contentDetails,statistics,snippet",
                    id=video_id
                ).execute()

                if not video_response["items"]:
                    continue

                video_details = video_response["items"][0]
                
                duration_str = video_details.get("contentDetails", {}).get("duration", "PT0M0S")
                duration_obj = isodate.parse_duration(duration_str)
                duration_minutes = duration_obj.total_seconds() / 60
                
                # Skip if video is too long or too short (e.g., less than 3 minutes)
                if max_duration_minutes and duration_minutes > max_duration_minutes:
                    continue
                if duration_minutes < 3:
                    continue
                
                title = video_details["snippet"]["title"]
                # Skip if title indicates a short video
                if any(tag in title.lower() for tag in ["#shorts", "#short", "#reels", "shorts"]):
                    continue
                
                hours, remainder = divmod(int(duration_obj.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                formatted_duration = f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"
                
                candidate_videos.append({
                    "title": title,
                    "channel": channel_title,
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                    "duration": formatted_duration,
                    "duration_minutes": round(duration_minutes, 1),
                    "views": video_details.get("statistics", {}).get("viewCount", "Unknown"),
                    "channel_id": video_details["snippet"].get("channelId", "")
                })
                
                if len(candidate_videos) >= 10:
                    break  # limit candidate pool
            
            # Look for a primary video whose title starts with 'Lec' or 'L'
            primary_video = None
            for video in candidate_videos:
                if re.match(r'^(lec|l)\b', video["title"].strip().lower()):
                    primary_video = video
                    break

            if primary_video:
                final_videos = [primary_video]
                channel_id = primary_video.get("channel_id")
                # Search the channel for additional videos
                if channel_id:
                    channel_response = self.youtube.search().list(
                        channelId=channel_id,
                        part="snippet",
                        maxResults=10,
                        type="video",
                        order="date"
                    ).execute()

                    additional_videos = []
                    for item in channel_response.get("items", []):
                        vid_id = item["id"]["videoId"]
                        # Skip if it's the same as the primary video
                        if vid_id == primary_video["video_id"]:
                            continue
                        
                        # Get video details for filtering
                        video_resp = self.youtube.videos().list(
                            part="contentDetails,statistics,snippet",
                            id=vid_id
                        ).execute()
                        if not video_resp["items"]:
                            continue
                        vid_details = video_resp["items"][0]
                        
                        dur_str = vid_details.get("contentDetails", {}).get("duration", "PT0M0S")
                        dur_obj = isodate.parse_duration(dur_str)
                        dur_minutes = dur_obj.total_seconds() / 60
                        if max_duration_minutes and dur_minutes > max_duration_minutes:
                            continue
                        if dur_minutes < 3:
                            continue
                        vid_title = vid_details["snippet"]["title"]
                        if any(tag in vid_title.lower() for tag in ["#shorts", "#short", "#reels", "shorts"]):
                            continue

                        hours, rem = divmod(int(dur_obj.total_seconds()), 3600)
                        mins, secs = divmod(rem, 60)
                        vid_formatted_duration = f"{hours}:{mins:02d}:{secs:02d}" if hours else f"{mins}:{secs:02d}"
                        
                        additional_videos.append({
                            "title": vid_title,
                            "channel": item["snippet"]["channelTitle"],
                            "video_id": vid_id,
                            "url": f"https://www.youtube.com/watch?v={vid_id}",
                            "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                            "duration": vid_formatted_duration,
                            "duration_minutes": round(dur_minutes, 1),
                            "views": vid_details.get("statistics", {}).get("viewCount", "Unknown")
                        })
                        
                        if len(additional_videos) >= 2:
                            break
                else:
                    additional_videos = []

                # Combine the primary video with the two additional ones
                final_videos.extend(additional_videos)
                # Ensure we return exactly 3 videos if available
                return final_videos[:3]
            else:
                # Fallback: if no primary video found, use up to 3 from the candidate list
                return candidate_videos[:3]
                
        except Exception as e:
            self.logger.error(f"Error searching YouTube: {str(e)}")
            return [{"error": f"Failed to search YouTube: {str(e)}"}]




    def _return_response(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Format the final response with topics and recommended videos."""
        topics_with_videos = request.get("topics_with_videos", [])
        metadata = request.get("metadata", {})

        prompt = self.type_prompts["RETURN_RESPONSE"]

        # Add the topics and videos information to the prompt
        prompt += f"\n\nTopics and videos information: {json.dumps(topics_with_videos, indent=2)}"

        response = self._call_llm(prompt, stage="RETURN_RESPONSE")

        return {
            "status": "success",
            "study_plan": response,
            "topics_with_videos": topics_with_videos,
            "metadata": metadata
        }

    def process_workflow(self, board: str, class_level: str, department: str, subject: str, max_duration_minutes: int = None) -> Dict[str, Any]:
        """
        Run the complete workflow from start to finish with efficiency improvements.
        
        Args:
            board: Educational board/university
            class_level: Class/year level
            department: Department/stream
            subject: Subject
            max_duration_minutes: Optional maximum video duration in minutes
        """
        try:
            # Step 1: Fetch question papers
            papers_request = {
                "type": "FETCH_QUESTION_PAPER",
                "board": board,
                "class_level": class_level,
                "department": department,
                "subject": subject
            }
            papers_response = self.process_request(papers_request)
            
            # Step 2: Analyze question papers
            analysis_request = {
                "type": "ANALYZE_QUESTION_PAPER",
                "paper": papers_response["papers_info"],
                "metadata": papers_response["metadata"]
            }
            analysis_response = self.process_request(analysis_request)

            # Step 3: Generate queries and fetch videos for each topic
            topics_with_videos = []
            # Ensure we only process 5 topics at most
            important_topics = analysis_response.get("important_topics", [])[:5]
            
            # Track all fetched video IDs to ensure uniqueness across topics
            all_video_ids = set()
            
            for topic in important_topics:
                query_request = {
                    "type": "GENERATE_QUERY",
                    "topic": topic["topic_name"],
                    "metadata": analysis_response["metadata"],
                    "max_duration_minutes": max_duration_minutes
                }
                query_response = self.process_request(query_request)
                
                # Filter out duplicates across topics
                unique_videos = []
                for video in query_response.get("videos", []):
                    video_id = video.get("video_id")
                    
                    # Only include videos we haven't seen before
                    if video_id and video_id not in all_video_ids:
                        all_video_ids.add(video_id)
                        unique_videos.append(video)
                
                # Add unique videos to the topic
                topic_with_videos = {
                    **topic,
                    "videos": unique_videos
                }
                topics_with_videos.append(topic_with_videos)

            # Step 4: Return the final response
            final_request = {
                "type": "RETURN_RESPONSE",
                "topics_with_videos": topics_with_videos,
                "metadata": analysis_response["metadata"]
            }
            final_response = self.process_request(final_request)

            return final_response
        except Exception as e:
            error_msg = f"Error in workflow: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}