from langchain_groq import ChatGroq
from agentic_kg.kg_retriever import KnowledgeGraphRetriever
from agentic_kg.cypher_agent import CypherAgent
from agentic_kg.condition_reasoner import ConditionReasoner
from agentic_kg.empathy_engine import EmpathyEngine
from dotenv import load_dotenv
import os

load_dotenv()

class AgenticKnowledgeGraph:

    def __init__(self):

        self.graph_retriever = KnowledgeGraphRetriever()

        self.cypher_agent = CypherAgent()

        self.reasoner = ConditionReasoner()

        self.empathy_engine = EmpathyEngine()

    def run(
        self,
        user_query
    ):

        # =====================================
        # STEP 1: CONDITION DETECTION
        # =====================================

        condition = self.cypher_agent.detect_condition(
            user_query
        )

        if not condition:

            return {
                "detected": False,
                "response": None
            }

        # =====================================
        # STEP 2: GRAPH RETRIEVAL
        # =====================================

        graph_data = self.graph_retriever.retrieve_condition_context(
            condition
        )

        # =====================================
        # STEP 3: AGENTIC REASONING
        # =====================================

        reasoning_response = self.reasoner.reason(
            graph_data,
            user_query
        )

        # =====================================
        # STEP 4: EMPATHY ENGINE
        # =====================================

        final_response = self.empathy_engine.enhance_response(
            user_query,
            reasoning_response
        )

        return {
            "detected": True,
            "condition": condition,
            "response": final_response
        }

if __name__ == "__main__":

    agent = AgenticKnowledgeGraph()

    while True:

        query = input("User: ")

        if query.lower() == "exit":
            break

        result = agent.run(query)

        print("\nAssistant:\n")

        print(result["response"])