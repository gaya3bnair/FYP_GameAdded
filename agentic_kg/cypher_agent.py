from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

class CypherAgent:

    def __init__(self):

        self.llm = ChatGroq(
            model_name="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0
        )

    def detect_condition(self, query):

        query_lower = query.lower()

        # OCD patterns
        ocd_keywords = [
            "obsession",
            "compulsion",
            "cleaning",
            "checking",
            "intrusive thoughts",
            "ritual",
            "repeating"
        ]

        # ADHD patterns
        adhd_keywords = [
            "can't focus",
            "distracted",
            "forgetting",
            "procrastinating",
            "attention",
            "hyperactive"
        ]

        # Anxiety patterns
        anxiety_keywords = [
            "panic",
            "stress",
            "overthinking",
            "fear",
            "worried",
            "anxious"
        ]

        for word in ocd_keywords:
            if word in query_lower:
                return "OCD"

        for word in adhd_keywords:
            if word in query_lower:
                return "ADHD"

        for word in anxiety_keywords:
            if word in query_lower:
                return "Anxiety"

        return None