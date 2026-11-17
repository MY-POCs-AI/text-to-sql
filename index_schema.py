
import os
import psycopg
import chromadb

from db_config import get_db_connection
from dotenv import load_dotenv

from openai import OpenAI
from google import genai
from mistralai import Mistral


# Chargement des variables d'environnement (.env)
load_dotenv()

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")

# Initialisation du client d'embeddings
if EMBEDDING_PROVIDER == "openai":
    embedding_client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )

elif EMBEDDING_PROVIDER == "google":
    embedding_client = genai.Client(
        api_key=os.getenv("GOOGLE_API_KEY")
    )

elif EMBEDDING_PROVIDER == "mistral":
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

collection = chroma_client.get_or_create_collection(
    name="database_schema"
)


def get_schema_documents():
    """
    Récupère la structure de PostgreSQL
    et construit un document par table.
    """

    conn = get_db_connection()

    documents = []
    ids = []
    metadatas = []

    try:
        with conn.cursor() as cur:

            # 1. Récupération des tables
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'text2sql_demo'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)

            tables = cur.fetchall()

            for (table_name,) in tables:

                description = f"Table : {table_name}\n"
                description += "Colonnes :\n"

                # 2. Récupération des colonnes
                cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'text2sql_demo'
                      AND table_name = %s
                    ORDER BY ordinal_position;
                """, (table_name,))

                columns = cur.fetchall()

                for column_name, data_type, nullable in columns:
                    description += (
                        f"- {column_name} : {data_type}, "
                        f"nullable : {nullable}\n"
                    )

                # 3. Récupération des clés étrangères
                cur.execute("""
                    SELECT
                        kcu.column_name,
                        ccu.table_name,
                        ccu.column_name
                    FROM information_schema.key_column_usage kcu
                    JOIN information_schema.constraint_column_usage ccu
                      ON kcu.constraint_name = ccu.constraint_name
                     AND kcu.constraint_schema = ccu.constraint_schema
                    WHERE kcu.table_schema = 'text2sql_demo'
                      AND kcu.table_name = %s
                      AND kcu.position_in_unique_constraint IS NOT NULL;
                """, (table_name,))

                foreign_keys = cur.fetchall()

                if foreign_keys:
                    description += "Relations :\n"

                    for column, foreign_table, foreign_column in foreign_keys:
                        description += (
                            f"- {column} référence "
                            f"{foreign_table}.{foreign_column}\n"
                        )

                documents.append(description)
                ids.append(f"table_{table_name}")
                metadatas.append({
                    "type": "table",
                    "table_name": table_name
                })

    finally:
        conn.close()

    return documents, ids, metadatas


def generate_embeddings(documents):
    """
    Génère les embeddings selon le fournisseur sélectionné.
    """

    if EMBEDDING_PROVIDER == "openai":

        response = embedding_client.embeddings.create(
            model="text-embedding-3-small",
            input=documents
        )

        return [
            item.embedding
            for item in sorted(response.data, key=lambda item: item.index)
        ]

    elif EMBEDDING_PROVIDER == "google":

        response = embedding_client.models.embed_content(
            model="gemini-embedding-001",
            contents=documents
        )

        return [item.values for item in response.embeddings]

    elif EMBEDDING_PROVIDER == "mistral":

        response = embedding_client.embeddings.create(
            model="mistral-embed",
            inputs=documents
        )

        return [
            item.embedding
            for item in sorted(response.data, key=lambda item: item.index)
        ]


def index_schema():

    # 1. Extraction de la structure de la BDD
    documents, ids, metadatas = get_schema_documents()

    print(f"{len(documents)} tables récupérées.")

    if not documents:
        print("Aucune table trouvée.")
        return

    # 2. Génération des embeddings
    embeddings = generate_embeddings(documents)

    # 3. Enregistrement dans ChromaDB
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(f"{len(documents)} documents indexés dans ChromaDB.")
    print("Nombre total de documents :", collection.count())


if __name__ == "__main__":
    index_schema()
