import os
from groq import Groq
from langchain.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings


class RagService:
    def __init__(self):
        # Use os.environ.get to fetch environment variable GROQ_API_KEY
        self.groq_client = Groq(
            api_key="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")
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = None

    def initialize(self, pdf_path: str):
        # Load the PDF file using PyPDFLoader
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        texts = text_splitter.split_documents(documents)
        self.vector_store = FAISS.from_documents(texts, self.embeddings)

    def get_context(self, question: str, k: int = 3) -> str:
        docs = self.vector_store.similarity_search(question, k=k)
        return "\n\n".join([doc.page_content for doc in docs])

    def generate_response(self, question: str, context: str) -> str:
        """Generate a response using the Groq API with the provided context."""
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are RapidRevise, the official assistant for RapidRevise 2025. "
                            f"Use this context to answer questions: {context}"
                        )
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                model="llama-3.2-90b-vision-preview",
                temperature=0.7,
                max_tokens=1024
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")



