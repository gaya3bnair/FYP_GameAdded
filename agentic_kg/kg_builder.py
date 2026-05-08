import os
import json
import re
import time
import fitz
import pytesseract

from PIL import Image
from io import BytesIO
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

# ==========================================
# CONFIG
# ==========================================

DOCS_PATH = "Docs"

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ==========================================
# LLM
# ==========================================

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name="llama-3.1-8b-instant",
    temperature=0
)

# ==========================================
# NEO4J
# ==========================================

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
)

# ==========================================
# PDF + OCR EXTRACTION
# ==========================================

def extract_pdf_text(pdf_path):

    doc = fitz.open(pdf_path)

    full_text = ""

    for page_num in range(len(doc)):

        page = doc[page_num]

        # normal extraction
        text = page.get_text()

        # OCR fallback
        if len(text.strip()) < 50:

            pix = page.get_pixmap()

            img = Image.open(
                BytesIO(pix.tobytes("png"))
            )

            text = pytesseract.image_to_string(img)

        full_text += text + "\n"

    return full_text

# ==========================================
# CHUNKING
# ==========================================

def chunk_text(text, chunk_size=2500):

    chunks = []

    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])

    return chunks

# ==========================================
# CLEAN JSON
# ==========================================

def extract_json(text):

    match = re.search(r'\{.*\}', text, re.DOTALL)

    if match:
        return match.group()

    return None

# ==========================================
# LLM GRAPH EXTRACTION
# ==========================================

def extract_graph(chunk):

    prompt = f"""
You are an expert mental health knowledge graph extraction system.

Extract entities and relationships related to:
- ADHD
- OCD
- Anxiety

Focus on:
- symptoms
- compulsions
- triggers
- therapies
- treatments
- medications
- coping strategies
- emotions
- behaviors
- ERP
- CBT

Return ONLY valid JSON.

Format:

{{
  "relationships": [
    {{
      "source": "OCD",
      "relationship": "HAS_SYMPTOM",
      "target": "Intrusive Thoughts"
    }}
  ]
}}

TEXT:
{chunk}
"""

    for attempt in range(3):

        try:

            response = llm.invoke(prompt)

            content = response.content

            json_text = extract_json(content)

            if not json_text:
                continue

            data = json.loads(json_text)

            return data

        except Exception as e:

            print(f"Retry {attempt+1}:", e)

            time.sleep(3)

    return None

# ==========================================
# SAVE TO NEO4J
# ==========================================

def save_graph(data):

    if not data:
        return

    with driver.session() as session:

        for rel in data["relationships"]:

            try:

                source = rel["source"].strip()
                relation = rel["relationship"].strip()
                target = rel["target"].strip()

                relation = relation.replace(" ", "_")

                query = f"""
                MERGE (a:Entity {{name:$source}})
                MERGE (b:Entity {{name:$target}})
                MERGE (a)-[:{relation}]->(b)
                """

                session.run(
                    query,
                    source=source,
                    target=target
                )

            except Exception as e:
                print("Neo4j error:", e)

# ==========================================
# MAIN
# ==========================================

def build_knowledge_graph():

    pdfs = list(Path(DOCS_PATH).glob("*.pdf"))

    for pdf in pdfs:

        print(f"\nProcessing: {pdf.name}")

        text = extract_pdf_text(str(pdf))

        print("Text extracted")

        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):

            print(f"Chunk {i+1}/{len(chunks)}")

            data = extract_graph(chunk)

            save_graph(data)

            time.sleep(2)

    print("\nKnowledge Graph Created Successfully")

# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":
    build_knowledge_graph()