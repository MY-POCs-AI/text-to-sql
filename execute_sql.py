from db_config import get_db_connection


def execute_sql(sql):
    """
    Execute une requete SQL en lecture seule
    et retourne les resultats.
    """

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            # Execution de la requete
            cur.execute(sql)

            # Recuperation des noms de colonnes
            columns = [desc.name for desc in cur.description]

            # Recuperation des donnees
            rows = cur.fetchall()

            # Transformation en dictionnaires Python
            results = [
                dict(zip(columns, row))
                for row in rows
            ]

            return results

    finally:
        conn.close()