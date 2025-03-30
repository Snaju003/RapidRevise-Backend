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
        already_selected_ids = request.get("already_selected_ids", set())
        
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
        
        # Ensure we have at least one query, use the original method as fallback
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
        
        # For each query, fetch videos
        videos = []
        
        for query in aspect_queries:
            aspect_videos = self._search_youtube_single(query, subject, max_duration_minutes)
            if aspect_videos:
                # Only add videos we haven't seen before
                for video in aspect_videos:
                    video_id = video.get("video_id")
                    if video_id and video_id not in already_selected_ids:
                        already_selected_ids.add(video_id)
                        videos.append(video)
                        break  # Just take one unique video per aspect
                
        return {
            "status": "success",
            "topic": topic,
            "search_queries": aspect_queries,
            "videos": videos,
            "already_selected_ids": already_selected_ids,
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

    def _sort_videos(self, videos, sort_by="relevance"):
        """
        Sort videos based on the specified criteria.
        
        Args:
            videos: List of video dictionaries
            sort_by: Sorting criteria - "relevance" (default), "duration", "views", "title"
        
        Returns:
            Sorted list of videos
        """
        if sort_by == "duration":
            # Sort by duration (shortest first)
            return sorted(videos, key=lambda x: x.get("duration_minutes", float("inf")))
        elif sort_by == "duration_desc":
            # Sort by duration (longest first)
            return sorted(videos, key=lambda x: x.get("duration_minutes", 0), reverse=True)
        elif sort_by == "views":
            # Sort by view count (most viewed first)
            return sorted(videos, key=lambda x: int(x.get("views", "0").replace(",", "") or "0"), reverse=True)
        elif sort_by == "title":
            # Sort alphabetically by title
            return sorted(videos, key=lambda x: x.get("title", "").lower())
        else:
            # Default to the original order (by relevance from YouTube API)
            return videos

    def _search_youtube_single(self, query: str, subject: str, max_duration_minutes: int = None) -> List[Dict[str, Any]]:
        """
        Search YouTube for videos on a topic from Gate Smashers channel specifically.
        """
        try:
            # Direct query that includes topic, subject and specifically targets Gate Smashers
            gate_smashers_query = f"{query} lectures {subject} Gate Smashers"
            print(gate_smashers_query)
            # First, find the Gate Smashers channel ID
            channel_search_response = self.youtube.search().list(
                q="Gate Smashers",
                part="snippet",
                maxResults=5,
                type="channel"
            ).execute()
            
            gate_smashers_channel_id = None
            for item in channel_search_response.get("items", []):
                if "Gate Smashers" in item["snippet"]["title"]:
                    gate_smashers_channel_id = item["snippet"]["channelId"]
                    break
            
            if not gate_smashers_channel_id:
                self.logger.warning("Gate Smashers channel not found")
                return []
                
            # Now search for videos from Gate Smashers on the topic
            channel_videos_response = self.youtube.search().list(
                q=gate_smashers_query,
                part="snippet",
                maxResults=15,  # Request more to filter
                type="video",
                channelId=gate_smashers_channel_id
            ).execute()
            
            # Process the videos from Gate Smashers
            candidate_videos = []
            already_selected_ids = set()  # Track video IDs to avoid duplicates within this search
            
            for item in channel_videos_response.get("items", []):
                video_id = item["id"]["videoId"]
                
                # Skip if we've already processed this video
                if video_id in already_selected_ids:
                    continue
                    
                already_selected_ids.add(video_id)
                
                # Get video details
                video_response = self.youtube.videos().list(
                    part="contentDetails,statistics,snippet",
                    id=video_id
                ).execute()

                if not video_response["items"]:
                    continue

                video_details = video_response["items"][0]
                
                # Filter by duration
                duration_str = video_details.get("contentDetails", {}).get("duration", "PT0M0S")
                duration_obj = isodate.parse_duration(duration_str)
                duration_minutes = duration_obj.total_seconds() / 60
                
                # Skip if video is too long and max_duration is specified
                if max_duration_minutes and duration_minutes > max_duration_minutes:
                    continue
                    
                # Skip if video is too short (likely a short)
                if duration_minutes < 3:
                    continue
                
                # Check title to filter out shorts
                title = video_details["snippet"]["title"].lower()
                if "#shorts" in title or "#short" in title or "#reels" in title or "shorts" in title:
                    continue
                
                # Format duration
                hours, remainder = divmod(int(duration_obj.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                formatted_duration = f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"
                
                # Add to candidates
                candidate_videos.append({
                    "title": item["snippet"]["title"],
                    "channel": "Gate Smashers",
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                    "duration": formatted_duration,
                    "duration_minutes": round(duration_minutes, 1),
                    "views": video_details.get("statistics", {}).get("viewCount", "Unknown")
                })
                
                # Stop if we have enough candidates
                if len(candidate_videos) >= 3:
                    break
            
            # Return up to 3 videos
            return candidate_videos[:3]
            
        except Exception as e:
            self.logger.error(f"Error searching YouTube: {str(e)}")
            return [{"error": f"Failed to search YouTube: {str(e)}"}]

    def _return_response(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Format the final response with topics and recommended videos."""
        topics_with_videos = request.get("topics_with_videos", [])
        total_video_minutes = request.get("total_video_minutes", 0)
        metadata = request.get("metadata", {})

        # First, get the original text response
        prompt = self.type_prompts["RETURN_RESPONSE"]
        prompt += f"\n\nTopics and videos information: {json.dumps(topics_with_videos, indent=2)}"
        prompt += f"\n\nTotal video duration: {total_video_minutes} minutes"
        text_response = self._call_llm(prompt, stage="RETURN_RESPONSE")
        
        # Now create a structured format prompt that explicitly uses the topics from topics_with_videos
        structuring_prompt = f"""
        Based on the study plan you just created, reformat it into an array of JSON objects with this structure:
        [
            {{
                "question": "What is the key concept of [topic]?",
                "recommendation": "Study this by watching [specific video] and focusing on [specific aspect]"
            }},
            // More question-recommendation pairs
        ]
        
        Create exactly 2 question-recommendation pairs for EACH of these topics, using the EXACT topic names:
        {", ".join([topic.get("topic_name", "Unknown Topic") for topic in topics_with_videos])}
        
        Make sure to use the actual topic names from the list above and do not substitute them with other topics.
        Include specific video recommendations from the available videos where possible.
        
        End with one overall study strategy question-recommendation pair.
        Return only valid JSON, nothing else.
        """
        
        # Get structured response 
        structured_json_str = self._call_llm(structuring_prompt, stage="RETURN_RESPONSE", temperature=0.4)
        
        # Try to extract just the JSON part
        try:
            # Find JSON array in the response
            json_start = structured_json_str.find('[')
            json_end = structured_json_str.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = structured_json_str[json_start:json_end]
                structured_plan = json.loads(json_str)
            else:
                # Try to parse the whole response as JSON
                structured_plan = json.loads(structured_json_str)
                
        except json.JSONDecodeError:
            # If JSON parsing fails, create a structured plan directly from the topics
            self.logger.warning("Failed to parse structured response as JSON. Creating structured plan from topics.")
            structured_plan = self._create_structured_plan_from_topics(topics_with_videos, total_video_minutes)

        # Validate that the structured plan contains questions for all topics
        topic_names = [topic.get("topic_name", "").lower() for topic in topics_with_videos]
        missing_topics = []
        
        # Check if each topic is represented in the structured plan
        for topic_name in topic_names:
            found = False
            for item in structured_plan:
                if topic_name.lower() in item.get("question", "").lower():
                    found = True
                    break
            if not found:
                missing_topics.append(topic_name)
        
        # If topics are missing, add them using the fallback method
        if missing_topics:
            self.logger.warning(f"Topics missing from structured plan: {missing_topics}")
            missing_topic_objects = [t for t in topics_with_videos if t.get("topic_name", "").lower() in missing_topics]
            additional_items = self._create_structured_plan_from_topics(missing_topic_objects, 0)
            structured_plan.extend(additional_items)

        return {
            "status": "success",
            "study_plan": structured_plan,
            "study_plan_text": text_response,
            "topics_with_videos": topics_with_videos,
            "total_video_minutes": total_video_minutes,
            "metadata": metadata
        }

    def _create_structured_plan_from_topics(self, topics: List[Dict[str, Any]], total_video_minutes: float) -> List[Dict[str, Any]]:
        """Create a structured study plan directly from topics and videos."""
        structured_plan = []
        
        for topic in topics:
            topic_name = topic.get("topic_name", "Unknown Topic")
            videos = topic.get("videos", [])
            importance = topic.get("importance", 5)
            
            # Add fundamental concepts question
            question1 = {
                "question": f"What are the key concepts of {topic_name}?",
                "recommendation": f"Focus on understanding the fundamentals of {topic_name}, which has an importance score of {importance}/10. "
            }
            
            # Add video recommendation if available
            if videos and len(videos) > 0:
                video_title = videos[0].get("title", "")
                video_duration = videos[0].get("duration", "")
                video_url = videos[0].get("url", "")
                question1["recommendation"] += f"Watch '{video_title}' ({video_duration}) available at {video_url}. "
            
            question1["recommendation"] += f"Allocate approximately {topic.get('prep_time_minutes', 30)} minutes to study this topic."
            structured_plan.append(question1)
            
            # Add practical application question
            question2 = {
                "question": f"How to solve problems related to {topic_name}?",
                "recommendation": f"Practice applying concepts from {topic_name} to solve problems. "
            }
            
            # Add second video recommendation if available
            if videos and len(videos) > 1:
                video_title = videos[1].get("title", "")
                video_duration = videos[1].get("duration", "")
                video_url = videos[1].get("url", "")
                question2["recommendation"] += f"Watch '{video_title}' ({video_duration}) available at {video_url}. "
            
            question2["recommendation"] += "Work through example problems and understand the application of theoretical concepts."
            structured_plan.append(question2)
        
        # Add overall study strategy if total_video_minutes is provided
        if total_video_minutes > 0:
            structured_plan.append({
                "question": "What is the best overall study strategy?",
                "recommendation": f"Allocate time based on topic importance scores. Focus on high-priority topics first. "
                                f"Complete all video content (approximately {total_video_minutes} minutes total) and supplement "
                                f"with practice questions from previous papers. Review the most important concepts right before the exam."
            })
        
        return structured_plan

    def process_workflow(self, board: str, class_level: str, department: str, subject: str, max_duration_minutes: int = None, sort_by: str = "relevance") -> Dict[str, Any]:
        """
        Run the complete workflow from start to finish with efficiency improvements.
        
        Args:
            board: Educational board/university
            class_level: Class/year level
            department: Department/stream
            subject: Subject
            max_duration_minutes: Optional maximum video duration in minutes
            sort_by: How to sort videos - "relevance" (default), "duration", "duration_desc", "views", "title"
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
            
            # Create a set to track unique video IDs across all topics
            all_video_ids = set()
            
            for topic in important_topics:
                query_request = {
                    "type": "GENERATE_QUERY",
                    "topic": topic["topic_name"],
                    "metadata": analysis_response["metadata"],
                    "max_duration_minutes": max_duration_minutes,
                    "already_selected_ids": all_video_ids  # Pass the already selected IDs
                }
                query_response = self.process_request(query_request)
                
                # Update our global set of video IDs with any new ones found
                if isinstance(query_response.get("already_selected_ids"), set):
                    all_video_ids.update(query_response.get("already_selected_ids"))
                
                # Sort the videos based on the specified criteria
                sorted_videos = self._sort_videos(query_response.get("videos", []), sort_by)
                
                # Add videos to the topic
                # Add videos to the topic
                topic_with_videos = {
                    **topic,
                    "videos": sorted_videos
                }

                # Calculate total time for this topic's videos
                total_minutes = sum(video.get("duration_minutes", 0) for video in topic_with_videos["videos"])
                topic_with_videos["total_video_minutes"] = round(total_minutes, 1)
                # Update prep_time_minutes to match the video duration
                topic_with_videos["prep_time_minutes"] = round(total_minutes, 1)

                topics_with_videos.append(topic_with_videos)

            # Sort topics by importance if applicable
            topics_with_videos = sorted(topics_with_videos, key=lambda x: x.get("importance", 0), reverse=True)

            # Collect all videos for overall time calculation
            all_videos = []
            for topic in topics_with_videos:
                all_videos.extend(topic.get("videos", []))
            
            # Calculate overall total time
            overall_total_minutes = sum(video.get("duration_minutes", 0) for video in all_videos)

            # Step 4: Return the final response
            final_request = {
                "type": "RETURN_RESPONSE",
                "topics_with_videos": topics_with_videos,
                "total_video_minutes": round(overall_total_minutes, 1),
                "metadata": analysis_response["metadata"]
            }
            final_response = self.process_request(final_request)

            return final_response
        except Exception as e:
            error_msg = f"Error in workflow: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}