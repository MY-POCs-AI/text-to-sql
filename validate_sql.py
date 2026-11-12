
import sqlglot
from sqlglot import exp


# Tables autorisées pour notre agent
ALLOWED_TABLES = {
    "clients",
    "commandes",
    "lignes_commandes",
    "produits",
    "employes",
    "departements",
}

# Nombre maximum de lignes
MAX_ROWS = 100


def validate_sql(sql):

    # 1. Analyse de la requête SQL
    try:
        statements = sqlglot.parse(sql, read="postgres")

    except sqlglot.errors.ParseError as error:
        return False, f"Erreur de syntaxe SQL : {error}", None

    # 2. Une seule instruction
    if len(statements) != 1:
        return False, "Une seule instruction SQL est autorisée.", None

    statement = statements[0]

    # 3. SELECT uniquement
    if not isinstance(statement, exp.Select):
        return False, "Seules les requêtes SELECT sont autorisées.", None


    # 4. Vérification des tables
    # On récupère les noms des CTE (WITH ... AS ...)
    cte_names = {
        cte.alias_or_name.lower()
        for cte in statement.find_all(exp.CTE)
    }

    tables = statement.find_all(exp.Table)

    for table in tables:

        table_name = table.name.lower()

        # Les CTE ne sont pas des tables physiques
        if table_name in cte_names:
            continue

        if table_name not in ALLOWED_TABLES:
            return False, f"Table interdite : {table_name}", None

        if table.db and table.db.lower() != "text2sql_demo":
            return False, f"Schéma interdit : {table.db}", None


    # 5. Vérification et ajout du LIMIT
    limit = statement.args.get("limit")

    if limit is None:

        statement.set(
            "limit",
            exp.Limit(
                expression=exp.Literal.number(MAX_ROWS)
            )
        )

    else:

        limit_value = limit.expression

        if not isinstance(limit_value, exp.Literal):
            return False, "La limite doit être une valeur numérique.", None

        if not limit_value.is_int:
            return False, "La limite doit être un entier.", None

        if int(limit_value.this) > MAX_ROWS:
            return False, f"Maximum autorisé : {MAX_ROWS} lignes.", None

        if int(limit_value.this) < 1:
            return False, "La limite doit être supérieure à zéro.", None

    # 6. Génération du SQL corrigé
    validated_sql = statement.sql(dialect="postgres")

    return True, "Requête SQL valide.", validated_sql
