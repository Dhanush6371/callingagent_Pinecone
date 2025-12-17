import os
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI

load_dotenv()

# Clients
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("bawarchi-menu")

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def embed(text: str):
    return openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    ).data[0].embedding


def search_menu(query: str, top_k: int = 5):
    query_vector = embed(query)

    result = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True
    )

    return [
        {
            "id": match["id"],
            "score": round(match["score"], 3),
            "category": match["metadata"]["category"],
            "price": match["metadata"]["price"]
        }
        for match in result["matches"]
    ]


if __name__ == "__main__":
    while True:
        q = input("\nSearch menu (or 'exit'): ")
        if q.lower() == "exit":
            break
        print(search_menu(q))
