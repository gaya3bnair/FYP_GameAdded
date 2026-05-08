import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

class KnowledgeGraphRetriever:

    def __init__(self):

        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(
                os.getenv("NEO4J_USERNAME"),
                os.getenv("NEO4J_PASSWORD")
            )
        )

    def retrieve_condition_context(
        self,
        condition
    ):

        query = """
        MATCH (c:Entity)-[r1]->(n1:Entity)

        WHERE toLower(c.name)=toLower($condition)

        OPTIONAL MATCH (n1)-[r2]->(n2:Entity)

        RETURN
            c.name AS source,
            type(r1) AS relation,
            n1.name AS target,

            type(r2) AS second_relation,
            n2.name AS second_target
        """

        with self.driver.session() as session:

            result = session.run(
                query,
                condition=condition
            )

            return [dict(r) for r in result]