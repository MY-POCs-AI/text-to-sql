
import os
import chromadb

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = chroma_client.get_collection(
    name="database_schema"
)


def search_schema(question, n_results=4):

    # 1. Transformer la question en embedding
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=question
    )

    question_embedding = response.data[0].embedding

    # 2. Rechercher les tables les plus pertinentes
    table_results = collection.query(
        query_embeddings=[question_embedding],
        n_results=min(n_results, collection.count()),
        where={"type": "table"}
    )

    table_documents = table_results["documents"][0]

    # 3. Récupérer systématiquement les documents de relations
    relation_results = collection.get(
        where={"type": "relation"}
    )

    relation_documents = relation_results["documents"]

    # 4. Construire le contexte final
    documents = relation_documents + table_documents

    # Suppression des éventuels doublons
    documents = list(dict.fromkeys(documents))

    return documents


if __name__ == "__main__":

    question = input("Pose ta question : ")

    documents = search_schema(question)

    print("\n=== CONTEXTE RETROUVE DANS LE RAG ===")

    for document in documents:
        print("\n------------------------------")
        print(document)
