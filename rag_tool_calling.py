from validate_sql import validate_sql
from search_schema import search_schema
from execute_sql import execute_sql
from display_results import display_results
from validate_sql import validate_sql

import os
import json

from dotenv import load_dotenv
from openai import OpenAI


# ==========================================
# 1. INITIALISATION
# ==========================================

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


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
# 3. QUESTION UTILISATEUR
# ==========================================

question = input("Pose ta question : ")


# ==========================================
# 4. RECHERCHE RAG DANS CHROMADB
# ==========================================

documents = search_schema(question)

schema_context = "\n\n".join(documents)

# print("\n=== CONTEXTE RAG RETROUVE ===")
# print(schema_context)


# ==========================================
# 5. ENVOI DE LA QUESTION A OPENAI
# ==========================================

instructions = f"""
Tu es un assistant SQL PostgreSQL.

Tu dois répondre aux questions concernant les données
de l'entreprise en utilisant l'outil execute_sql.

Voici le schéma de la base de données retrouvé par le RAG :

{schema_context}

REGLES IMPORTANTES :

- Utilise uniquement les tables et colonnes présentes dans le schéma.
- Respecte les relations entre les tables.
- Génère uniquement des requêtes SQL PostgreSQL en SELECT.
- N'invente jamais de table ou de colonne.
- Utilise les jointures appropriées lorsque plusieurs tables sont nécessaires.
- Si les informations disponibles sont insuffisantes, explique-le.
- Appelle l'outil execute_sql pour obtenir les données.
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

response = client.responses.create(
    model="gpt-5-mini",
    instructions=instructions,
    input=question,
    tools=tools
)



# ==========================================
# 6. DETECTION ET EXECUTION DE L'OUTIL
# ==========================================

for item in response.output:

    if item.type == "function_call":

        arguments = json.loads(item.arguments)
        sql = arguments["sql"]

        # ----------------------------------
        # VALIDATION SQL
        # ----------------------------------

        valid, message, validated_sql = validate_sql(sql)

        if not valid:

            print("\n=== REQUETE SQL REFUSEE ===")
            print(message)

            tool_output = f"Requête SQL refusée : {message}"
            raise SystemExit(0)

        else:

            print("\n=== REQUETE SQL VALIDEE ===")
            print(message)

            print("\nRequête SQL validée :")
            print(validated_sql)

            confirmation = input(
                "\nExécuter cette requête ? (o/n) : "
            )

            if confirmation.lower() == "o":

                results = execute_sql(validated_sql)

                # Affichage des résultats dans le terminal
                display_results(results)

                # Transmission des résultats à OpenAI
                tool_output = json.dumps(
                    results,
                    ensure_ascii=False,
                    default=str
                )

            else:

                tool_output = "Exécution annulée par l'utilisateur."

        # print("\nRésultat SQL :")
        # print(tool_output)

        # -------------------------------------------------------------------------------
        # RETOUR DES RESULTATS A OPENAI // Text et Calcul généré par le LLM:Moins fiable
        # -------------------------------------------------------------------------------

        # second_response = client.responses.create(
        #     model="gpt-5-mini",
        #     previous_response_id=response.id,
        #     input=[
        #         {
        #             "type": "function_call_output",
        #             "call_id": item.call_id,
        #             "output": tool_output
        #         }
        #     ],
        #     tools=tools
        # )

        # print("\n=== REPONSE FINALE DE L'IA ===")
        # print(second_response.output_text)


        print("\n=== RESULTAT FINAL ===")

        if results:
            # Cas 1 : montant global calculé par SQL
            if "chiffre_affaires_total" in results[0]:
                montant = results[0]["chiffre_affaires_total"]
                print(f"Chiffre d'affaires total : {montant:,.2f} €")

            # Cas 2 : montant calculé pour chaque commande
            elif "montant_total" in results[0] and "commande_id" in results[0]:
                montant_cumule = sum(
                    row["montant_total"] or 0 for row in results
                )

                print(f"{len(results)} commande(s) trouvée(s).\n")

                for row in results:
                    print(
                        f"Commande {row['commande_id']} : "
                        f"{row['montant_total']:,.2f} €"
                    )

                print(f"\nMontant cumulé : {montant_cumule:,.2f} €")

            # Cas 3 : résultat générique
            else:
                print(f"{len(results)} résultat(s) retourné(s).")

        else:
            print("Aucun résultat trouvé.")


# ==========================================
# 7. SI AUCUN OUTIL N'A ETE APPELE
# ==========================================

if not any(item.type == "function_call" for item in response.output):

    print("\n=== REPONSE DE L'IA ===")
    print(response.output_text)
