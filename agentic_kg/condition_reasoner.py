from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

class ConditionReasoner:

    def __init__(self):

        self.llm = ChatGroq(
            model_name="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0
        )

    def reason(
        self,
        graph_data,
        user_query
    ):

        context = []

        for row in graph_data:

            context.append(
                f"{row['source']} {row['relation']} {row['target']}"
            )

        graph_context = "\n".join(context)

        prompt = f"""
You are a mental health reasoning AI.

Use ONLY the graph knowledge below.

Graph Knowledge:
{graph_context}

User Query:
{user_query}

Your job:
- analyze the user's concern
- identify relevant symptoms/triggers/coping methods
- provide structured educational guidance
- connect concepts logically
- use ONLY graph knowledge

Do NOT diagnose.

Return:
- understanding
- explanation
- coping guidance
"""

        response = self.llm.invoke(prompt)

        return response.content