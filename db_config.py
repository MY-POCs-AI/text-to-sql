import os
import psycopg

from dotenv import load_dotenv

# Chargement des variables du fichier .env
load_dotenv()


def get_db_connection():
    """
    Retourne une connexion à PostgreSQL
    avec les paramètres définis dans .env.
    """

    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "entreprise"),
        user=os.getenv("DB_USER", "ai_reader"),
        password=os.getenv("DB_PASSWORD"),
        options="-c search_path=text2sql_demo"
    )