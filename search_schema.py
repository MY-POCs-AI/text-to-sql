
import os
import chromadb

from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")

# Initialisation du client d'embeddings
if EMBEDDING_PROVIDER == "openai":
    from openai import OpenAI

    embedding_client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )

elif EMBEDDING_PROVIDER == "google":
    from google import genai

    embedding_client = genai.Client(
        api_key=os.getenv("GOOGLE_API_KEY")
    )

elif EMBEDDING_PROVIDER == "mistral":
    from mistralai.client import Mistral

    embedding_client = Mistral(
        api_key=os.getenv("MISTRAL_API_KEY")
    )

else:
    raise ValueError(
        f"Fournisseur d'embeddings non supporté : {EMBEDDING_PROVIDER}"
    )


# Connexion à ChromaDB
chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = chroma_client.get_collection(
    name="database_schema"
)


def generate_embedding(question):
    """
    Génère l'embedding d'une question selon le fournisseur configuré.
    """

    if EMBEDDING_PROVIDER == "openai":

        response = embedding_client.embeddings.create(
            model="text-embedding-3-small",
            input=question
        )

        return response.data[0].embedding

    elif EMBEDDING_PROVIDER == "google":

        response = embedding_client.models.embed_content(
            model="gemini-embedding-001",
            contents=question
        )

        return response.embeddings[0].values

    elif EMBEDDING_PROVIDER == "mistral":

        response = embedding_client.embeddings.create(
            model="mistral-embed",
            inputs=question
        )

        return response.data[0].embedding


def search_schema(question, n_results=4):

    # 1. Transformer la question en embedding
    question_embedding = generate_embedding(question)

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
