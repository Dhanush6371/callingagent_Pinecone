import os
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
from menu_data import MENU_ITEMS

load_dotenv()


pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("bawarchi-menu")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def embed(text):
    return client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    ).data[0].embedding

vectors = []

for item in MENU_ITEMS:
    vectors.append({
        "id": item["id"],
        "values": embed(item["text"]),
        "metadata": item["metadata"]
    })

index.upsert(vectors=vectors)
print("✅ Menu indexed successfully")
