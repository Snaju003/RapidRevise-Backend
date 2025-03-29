import logging
import json
from typing import Dict, List, Any, Union
from groq import Groq
import os
from googleapiclient.discovery import build
from langchain_fireworks import Fireworks


class ExamPrepAgent:
    def __init__(self, groq_fetch_paper_api_key: str, groq_extract_topic_api_key: str, groq_gen_query_api_key: str, groq_struct_res_api_key: str, youtube_api_key: str):
        self.groq_fetch_paper = Groq(api_key=groq_fetch_paper_api_key)
        self.groq_extract_topic = Groq(api_key=groq_extract_topic_api_key)
        self.groq_gen_query = Groq(api_key=groq_gen_query_api_key)
        self.groq_struct_res = Groq(api_key=groq_struct_res_api_key)
        # self.groq = Fireworks(
        #     api_key=groq_api_key,
        #     model="llama-3.3-70b-versatilels/llama-v3p1-405b-instruct",
        # )
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
            """,
            "ANALYZE_QUESTION_PAPER": """
                Extract the most occurring or likely-to-be-asked topics from these question papers:
                {paper}

                Provide your analysis as a structured list of topics(hardly 5) with their importance metrics.
            """,
            "GENERATE_QUERY": """
                Generate a search query string for YouTube based on the topics: "{topic}" in {subject} for {board} {class_level} {department}.

                Format each query to maximize the likelihood of finding high-quality, targeted content.
            """,
            "RETURN_RESPONSE": """
                Organize the exam preparation materials into a structured response for the student.

                For each important topic:
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

    def _call_llm(self, prompt: str, temperature: float = 0.7, stage: str) -> str:
        """Call the Fireworks LLM with the given prompt."""
        try:
            self.logger.info("Calling LLM with prompt")

            if stage == "FETCH_QUESTION_PAPER":
                chat_completion = self.groq_fetch_paper.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",  # Using LLaMA 3 70B model
                    temperature=temperature,
                    max_tokens=4096
                )
            elif stage == "ANALYZE_QUESTION_PAPER":
                chat_completion = self.groq_extract_topic.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",  # Using LLaMA 3 70B model
                    temperature=temperature,
                    max_tokens=4096
                )
            elif stage == "GENERATE_QUERY":
                chat_completion = self.groq_gen_query.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",  # Using LLaMA 3 70B model
                    temperature=temperature,
                    max_tokens=4096
                )
            elif stage == "RETURN_RESPONSE":
                chat_completion = self.groq_struct_res.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",  # Using LLaMA 3 70B model
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
        # Changed variable name from 'class' to 'class_level'
        class_level = request.get("class_level", "")
        department = request.get("department", "")
        subject = request.get("subject", "")

        prompt = self.type_prompts["FETCH_QUESTION_PAPER"].format(
            board=board,
            class_level=class_level,  # Using class_level instead of class
            department=department,
            subject=subject,
        )

        response = self._call_llm(prompt, stage="FETCH_QUESTION_PAPER")

        # In a real implementation, this would trigger actual paper fetching
        # For now, we just return the LLM's structured guidance
        return {
            "status": "success",
            "papers_info": response,
            "metadata": {
                "board": board,
                "class_level": class_level,  # Changed to class_level
                "department": department,
                "subject": subject
            }
        }

    def _analyze_question_papers(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the provided question papers to identify key topics."""
        papers = request.get("paper", "")
        subject = request.get("metadata", {}).get("subject", "")
        board = request.get("metadata", {}).get("board", "")
        class_level = request.get("metadata", {}).get(
            "class_level", "")  # Changed to class_level
        department = request.get("metadata", {}).get("department", "")

        prompt = self.type_prompts["ANALYZE_QUESTION_PAPER"].format(
            paper=papers,
            subject=subject,
            board=board,
            class_level=class_level,  # Using class_level
            department=department,
        )

        response = self._call_llm(prompt, stage="ANALYZE_QUESTION_PAPER")

        # Parse the response to extract topics
        # This would be more sophisticated in a real implementation
        try:
            # Attempt to extract structured information about topics
            topics = self._extract_topics(response)
            return {
                "status": "success",
                "important_topics": topics,
                "raw_analysis": response,
                "metadata": {
                    "board": board,
                    "class_level": class_level,  # Changed to class_level
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
                    "class_level": class_level,  # Changed to class_level
                    "department": department,
                    "subject": subject
                }
            }

    def _extract_topics(self, analysis_text: str) -> List[Dict[str, Any]]:
        """Extract structured topic information from the LLM analysis."""
        # In a real implementation, this would use regex or more sophisticated parsing
        # For now, we'll ask the LLM to structure its own output

        structuring_prompt = """
        Based on your previous analysis, extract just the list of important topics in the following JSON format:
        [
            {
                "topic_name": "Name of the topic",
                "importance": 8,  // Scale of 1-10
                "prep_time_minutes": 60  // Estimated preparation time in minutes
            },
            // More topics...
        ]
        
        Only respond with the valid JSON array, nothing else.
        """

        structured_response = self._call_llm(
            prompt=structuring_prompt,
            temperature=0.7,
            stage="ANALYZE_QUESTION_PAPER"
        )

        # Try to extract just the JSON part
        try:
            # Find JSON in the response (assuming it might have text before/after)
            json_start = structured_response.find('[')
            json_end = structured_response.rfind(']') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = structured_response[json_start:json_end]
                return json.loads(json_str)
            else:
                # Fallback - try to parse the whole response
                return json.loads(structured_response)
        except json.JSONDecodeError:
            # If we can't parse as JSON, return a simple structure
            self.logger.warning(
                "Failed to parse LLM output as JSON, creating simple structure")
            return [{"topic_name": "Topic extraction failed", "raw_analysis": structured_response}]

    def _generate_query(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimized search queries for the given topic."""
        topic = request.get("topic", "")
        subject = request.get("metadata", {}).get("subject", "")
        board = request.get("metadata", {}).get("board", "")
        class_level = request.get("metadata", {}).get(
            "class_level", "")  # Changed to class_level
        department = request.get("metadata", {}).get("department", "")

        prompt = self.type_prompts["GENERATE_QUERY"].format(
            topic=topic,
            subject=subject,
            board=board,
            class_level=class_level,  # Using class_level
            department=department
        )

        response = self._call_llm(prompt)

        # Extract search queries from the response
        search_queries = self._extract_search_queries(response)

        # Fetch videos for each query
        videos = []
        for query in search_queries:
            print("SEARCH_QUERIES:"+str(search_queries))
            query_videos = self._search_youtube(query)
            videos.extend(query_videos)

        return {
            "status": "success",
            "topic": topic,
            "search_queries": search_queries,
            "videos": videos,
            "metadata": {
                "board": board,
                "class_level": class_level,  # Changed to class_level
                "department": department,
                "subject": subject
            }
        }

    def _extract_search_queries(self, query_text: str) -> List[str]:
        """Extract search queries from the LLM response."""
        # In a real implementation, this would be more sophisticated
        # For simplicity, we'll look for numbered lists or quotes
        import re

        # Look for quotes (text between quotation marks)
        quoted_queries = re.findall(r'"([^"]*)"', query_text)
        if quoted_queries:
            return quoted_queries[:3]  # Return up to 3 queries

        # Look for numbered list items
        numbered_items = re.findall(r'\d+\.\s+(.*?)(?:\n|$)', query_text)
        if numbered_items:
            return numbered_items[:3]

        # Fallback: just split by newlines and take non-empty lines
        lines = [line.strip()
                 for line in query_text.split('\n') if line.strip()]
        return lines[:3] if lines else ["Failed to extract queries"]

    def _search_youtube(self, query: str) -> List[Dict[str, Any]]:
        """Search YouTube for videos matching the query."""
        try:
            search_response = self.youtube.search().list(
                q=query,
                part="snippet",
                maxResults=3,
                type="video"
            ).execute()

            videos = []
            for item in search_response.get("items", []):
                video_id = item["id"]["videoId"]

                # Get video details (including duration)
                video_response = self.youtube.videos().list(
                    part="contentDetails,statistics",
                    id=video_id
                ).execute()

                video_details = video_response["items"][0] if video_response["items"] else {
                }

                videos.append({
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                    "duration": video_details.get("contentDetails", {}).get("duration", "Unknown"),
                    "views": video_details.get("statistics", {}).get("viewCount", "Unknown")
                })

            return videos
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

    def process_workflow(self, board: str, class_level: str, department: str, subject: str) -> Dict[str, Any]:
        """Run the complete workflow from start to finish."""
        try:
            # Step 1: Fetch question papers
            papers_request = {
                "type": "FETCH_QUESTION_PAPER",
                "board": board,
                "class_level": class_level,  # Still using 'class' in the input request
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
            for topic in analysis_response.get("important_topics", []):
                query_request = {
                    "type": "GENERATE_QUERY",
                    "topic": topic["topic_name"],
                    "metadata": analysis_response["metadata"]
                }
                query_response = self.process_request(query_request)

                # Add videos to the topic
                topic_with_videos = {
                    **topic,
                    "videos": query_response.get("videos", [])
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
