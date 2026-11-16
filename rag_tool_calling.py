from validate_sql import validate_sql
from search_schema import search_schema
from execute_sql import execute_sql
from display_results import display_results

import os
import json

from dotenv import load_dotenv
from openai import OpenAI


# ==========================================
# 1. INITIALISATION
# ==========================================

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ==========================================
# 2. DEFINITION DE L'OUTIL SQL
# ==========================================

tools = [
    {
        "type": "function",
        "name": "execute_sql",
        "description": "Execute une requete SQL SELECT sur PostgreSQL et retourne les resultats.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "La requete SQL SELECT a executer."
                }
            },
            "required": ["sql"],
            "additionalProperties": False
        },
        "strict": True
    }
]


# ==========================================
# 3. INSTRUCTIONS DE L'AGENT
# ==========================================

BASE_INSTRUCTIONS = """
Tu es un assistant SQL PostgreSQL.

Tu dois répondre aux questions concernant les données
de l'entreprise en utilisant l'outil execute_sql.

REGLES IMPORTANTES :

- Utilise uniquement les tables et colonnes présentes dans le schéma.
- Respecte les relations entre les tables.
- Génère uniquement des requêtes SQL PostgreSQL en SELECT.
- N'invente jamais de table ou de colonne.
- Utilise les jointures appropriées lorsque plusieurs tables sont nécessaires.

GESTION DES AMBIGUITES :

- Ne demande pas systématiquement des précisions.
- Si une interprétation raisonnable est possible, utilise-la et génère directement le SQL.
- Pour les ambiguïtés mineures, choisis des hypothèses cohérentes avec les données disponibles.
- Ne demande jamais de confirmer des hypothèses que tu peux raisonnablement choisir.
- Demande une précision uniquement lorsqu'une information indispensable manque ou lorsque plusieurs interprétations conduisent à des résultats fondamentalement différents.
- Si tu demandes une précision, pose uniquement les questions indispensables.
- Lorsque l'utilisateur apporte une précision, tiens compte de toute la conversation.
- Appelle execute_sql uniquement lorsque la question est suffisamment précise.

REGLES METIER :

- Pour les recherches de produits, utilise par défaut des correspondances textuelles insensibles à la casse avec ILIKE.
- Pour une commande ultérieure, considère par défaut que date_commande doit être strictement supérieure à la date de la première commande.
- Pour calculer le chiffre d'affaires, utilise toujours lignes_commandes.quantite * lignes_commandes.prix_unitaire. Ne jamais utiliser produits.prix, qui correspond au prix catalogue actuel.
- Analyse toujours la question dans son ensemble avant de générer le SQL.
- Une question peut nécessiter plusieurs opérations SQL : filtrage, jointures, regroupements, classement et calculs.
- Ne te limite jamais à identifier les produits si l'utilisateur demande également un classement de clients ou un calcul de chiffre d'affaires.
- Pour identifier le client ayant acheté le plus d'unités d'un produit, utilise SUM(quantite), regroupe par client et trie par quantité décroissante.
- Si l'utilisateur demande ensuite le chiffre d'affaires de ce client, calcule SUM(quantite * prix_unitaire) pour les produits concernés et ce client.
- Utilise une CTE ou une sous-requête si plusieurs étapes de calcul sont nécessaires.
- Pour identifier un produit, ne confonds pas le produit lui-même avec ses accessoires. Par exemple, "ordinateur" ne doit pas inclure automatiquement une sacoche d'ordinateur.
- Génère une requête SQL complète qui répond à toute la question, et non une requête intermédiaire.
"""


# ==========================================
# 4. BOUCLE PRINCIPALE
# ==========================================

print("\n=== AI SQL AGENT ===")
print("Tape 'quitter' pour arrêter le programme.\n")

while True:

    question = input("\nPose ta question : ").strip()

    if question.lower() in ["quitter", "exit", "quit"]:
        print("\nFin du programme.")
        break

    if not question:
        continue

    # ==========================================
    # 5. RECHERCHE RAG
    # ==========================================

    documents = search_schema(question)
    schema_context = "\n\n".join(documents)

    instructions = f"""
{BASE_INSTRUCTIONS}

Voici le schéma de la base de données retrouvé par le RAG :

{schema_context}
"""

    # ==========================================
    # 6. PREMIER APPEL A OPENAI
    # ==========================================

    response = client.responses.create(
        model="gpt-5-mini",
        instructions=instructions,
        input=question,
        tools=tools
    )

    action_terminee = False

    # ==========================================
    # 7. BOUCLE DE CONVERSATION
    # ==========================================

    while True:

        function_calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        # --------------------------------------
        # CAS 1 : L'IA DEMANDE UNE PRECISION
        # --------------------------------------

        if not function_calls:

            if action_terminee:
                break

            print("\n=== REPONSE DE L'IA ===")
            print(response.output_text)

            precision = input(
                "\nTa précision (ou 'nouvelle' pour une autre question) : "
            ).strip()

            if precision.lower() in ["nouvelle", "/new"]:
                break

            if precision.lower() in ["quitter", "exit", "quit"]:
                print("\nFin du programme.")
                raise SystemExit(0)

            if not precision:
                continue

            response = client.responses.create(
                model="gpt-5-mini",
                instructions=instructions,
                previous_response_id=response.id,
                input=precision,
                tools=tools
            )

            continue

        # --------------------------------------
        # CAS 2 : L'IA APPELLE L'OUTIL SQL
        # --------------------------------------

        tool_outputs = []

        for item in function_calls:

            arguments = json.loads(item.arguments)
            sql = arguments["sql"]

            # Validation SQL
            valid, message, validated_sql = validate_sql(sql)

            if not valid:

                print("\n=== REQUETE SQL REFUSEE ===")
                print(message)

                tool_output = f"Requête SQL refusée : {message}"

            else:

                print("\n=== REQUETE SQL VALIDEE ===")
                print(message)

                print("\nRequête SQL validée :")
                print(validated_sql)

                confirmation = input(
                    "\nExécuter cette requête ? (o/n) : "
                ).strip().lower()

                if confirmation == "o":

                    results = execute_sql(validated_sql)

                    display_results(results)

                    tool_output = json.dumps(
                        results,
                        ensure_ascii=False,
                        default=str
                    )

                    action_terminee = True

                else:

                    print("\nExécution annulée.")

                    tool_output = "Exécution annulée par l'utilisateur."

                    action_terminee = True

            tool_outputs.append({
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": tool_output
            })

        # --------------------------------------
        # 8. RETOUR DES RESULTATS A OPENAI
        # --------------------------------------

        if action_terminee:
            break

        response = client.responses.create(
            model="gpt-5-mini",
            instructions=instructions,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=tools
        )
