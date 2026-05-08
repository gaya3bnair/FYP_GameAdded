from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

class EmpathyEngine:

    def __init__(self):

        self.llm = ChatGroq(
            model_name="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.7
        )

    def enhance_response(
        self,
        user_query,
        reasoning_response,
        sentiment_score=None
    ):

        prompt = f"""
You are an emotionally intelligent mental wellness assistant.

Your job:
- make the response empathetic
- emotionally supportive
- calming
- non-judgmental
- psychologically safe

Do NOT diagnose.
Do NOT sound robotic.

User Query:
{user_query}

Knowledge Grounded Response:
{reasoning_response}

Create:
1. emotional validation
2. supportive explanation
3. gentle coping advice
4. hopeful tone
5. structured readability

Final Response:
"""

        response = self.llm.invoke(prompt)

        return response.content