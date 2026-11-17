
import os
import json

from dotenv import load_dotenv

from validate_sql import validate_sql
from search_schema import search_schema
from execute_sql import execute_sql
from display_results import display_results


# ==========================================
# 1. INITIALISATION
# ==========================================

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

if LLM_PROVIDER == "openai":
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    MODEL = "gpt-5-mini"

elif LLM_PROVIDER == "anthropic":
    from anthropic import Anthropic

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    MODEL = "claude-opus-5-5"

elif LLM_PROVIDER == "google":
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    MODEL = "gemini-3.8-flash"

elif LLM_PROVIDER == "mistral":
    from mistralai import Mistral

    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    MODEL = "mistral-small-latest"

else:
    raise ValueError(
        f"Fournisseur LLM non supporté : {LLM_PROVIDER}"
    )


# ==========================================
# 2. DEFINITION DE L'OUTIL SQL
# ==========================================

TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "sql": {
            "type": "string",
            "description": "La requête SQL SELECT à exécuter."
        }
    },
    "required": ["sql"],
    "additionalProperties": False
}


if LLM_PROVIDER == "openai":

    tools = [
        {
            "type": "function",
            "name": "execute_sql",
            "description": "Exécute une requête SQL SELECT sur PostgreSQL et retourne les résultats.",
            "parameters": TOOL_PARAMETERS,
            "strict": True
        }
    ]

elif LLM_PROVIDER == "anthropic":

    tools = [
        {
            "name": "execute_sql",
            "description": "Exécute une requête SQL SELECT sur PostgreSQL et retourne les résultats.",
            "input_schema": TOOL_PARAMETERS
        }
    ]

elif LLM_PROVIDER == "google":

    tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="execute_sql",
                    description="Exécute une requête SQL SELECT sur PostgreSQL et retourne les résultats.",
                    parameters=TOOL_PARAMETERS
                )
            ]
        )
    ]

elif LLM_PROVIDER == "mistral":

    tools = [
        {
            "type": "function",
            "function": {
                "name": "execute_sql",
                "description": "Exécute une requête SQL SELECT sur PostgreSQL et retourne les résultats.",
                "parameters": TOOL_PARAMETERS
            }
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
# 4. FONCTIONS DE COMMUNICATION AVEC LE LLM
# ==========================================

def start_conversation(question, instructions):

    if LLM_PROVIDER == "openai":

        conversation = {}

        response = client.responses.create(
            model=MODEL,
            instructions=instructions,
            input=question,
            tools=tools
        )

    elif LLM_PROVIDER == "anthropic":

        conversation = {
            "messages": [
                {"role": "user", "content": question}
            ]
        }

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=instructions,
            messages=conversation["messages"],
            tools=tools
        )

    elif LLM_PROVIDER == "google":

        conversation = {
            "chat": client.chats.create(
                model=MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=instructions,
                    tools=tools
                )
            )
        }

        response = conversation["chat"].send_message(question)

    elif LLM_PROVIDER == "mistral":

        conversation = {
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": question}
            ]
        }

        response = client.chat.complete(
            model=MODEL,
            messages=conversation["messages"],
            tools=tools
        )

    return conversation, response


def continue_conversation(conversation, response, user_input=None, tool_results=None):

    if LLM_PROVIDER == "openai":

        if tool_results is not None:

            response_input = [
                {
                    "type": "function_call_output",
                    "call_id": call["id"],
                    "output": output
                }
                for call, output in tool_results
            ]

        else:
            response_input = user_input

        return client.responses.create(
            model=MODEL,
            instructions=current_instructions,
            previous_response_id=response.id,
            input=response_input,
            tools=tools
        )

    elif LLM_PROVIDER == "anthropic":

        conversation["messages"].append({
            "role": "assistant",
            "content": response.content
        })

        if tool_results is not None:

            content = [
                {
                    "type": "tool_result",
                    "tool_use_id": call["id"],
                    "content": output
                }
                for call, output in tool_results
            ]

        else:
            content = user_input

        conversation["messages"].append({
            "role": "user",
            "content": content
        })

        return client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=current_instructions,
            messages=conversation["messages"],
            tools=tools
        )

    elif LLM_PROVIDER == "google":

        if tool_results is not None:

            parts = [
                types.Part.from_function_response(
                    name="execute_sql",
                    response={"result": output}
                )
                for call, output in tool_results
            ]

            return conversation["chat"].send_message(parts)

        return conversation["chat"].send_message(user_input)

    elif LLM_PROVIDER == "mistral":

        conversation["messages"].append(
            response.choices[0].message.model_dump(exclude_unset=True)
        )

        if tool_results is not None:

            for call, output in tool_results:

                conversation["messages"].append({
                    "role": "tool",
                    "name": "execute_sql",
                    "tool_call_id": call["id"],
                    "content": output
                })

        else:

            conversation["messages"].append({
                "role": "user",
                "content": user_input
            })

        return client.chat.complete(
            model=MODEL,
            messages=conversation["messages"],
            tools=tools
        )


# ==========================================
# 5. NORMALISATION DES REPONSES
# ==========================================

def get_tool_calls(response):

    calls = []

    if LLM_PROVIDER == "openai":

        for item in response.output:

            if item.type == "function_call":
                calls.append({
                    "id": item.call_id,
                    "arguments": json.loads(item.arguments)
                })

    elif LLM_PROVIDER == "anthropic":

        for item in response.content:

            if item.type == "tool_use":
                calls.append({
                    "id": item.id,
                    "arguments": item.input
                })

    elif LLM_PROVIDER == "google":

        for part in response.candidates[0].content.parts:

            if part.function_call:
                calls.append({
                    "id": part.function_call.id or part.function_call.name,
                    "arguments": dict(part.function_call.args)
                })

    elif LLM_PROVIDER == "mistral":

        message = response.choices[0].message

        for item in message.tool_calls or []:

            arguments = item.function.arguments

            if isinstance(arguments, str):
                arguments = json.loads(arguments)

            calls.append({
                "id": item.id,
                "arguments": arguments
            })

    return calls


def get_response_text(response):

    if LLM_PROVIDER == "openai":
        return response.output_text or ""

    elif LLM_PROVIDER == "anthropic":

        return "\n".join(
            item.text
            for item in response.content
            if item.type == "text"
        )

    elif LLM_PROVIDER == "google":
        return response.text or ""

    elif LLM_PROVIDER == "mistral":

        content = response.choices[0].message.content

        return content if isinstance(content, str) else ""


# ==========================================
# 6. BOUCLE PRINCIPALE
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
    # 7. RECHERCHE RAG
    # ==========================================

    documents = search_schema(question)
    schema_context = "\n\n".join(documents)

    current_instructions = f"""
{BASE_INSTRUCTIONS}

Voici le schéma de la base de données retrouvé par le RAG :

{schema_context}
"""

    # ==========================================
    # 8. PREMIER APPEL AU LLM
    # ==========================================

    conversation, response = start_conversation(
        question,
        current_instructions
    )

    action_terminee = False

    # ==========================================
    # 9. BOUCLE DE CONVERSATION
    # ==========================================

    while True:

        function_calls = get_tool_calls(response)

        # --------------------------------------
        # CAS 1 : L'IA DEMANDE UNE PRECISION
        # --------------------------------------

        if not function_calls:

            if action_terminee:
                break

            print("\n=== REPONSE DE L'IA ===")
            print(get_response_text(response))

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

            response = continue_conversation(
                conversation,
                response,
                user_input=precision
            )

            continue

        # --------------------------------------
        # CAS 2 : L'IA APPELLE L'OUTIL SQL
        # --------------------------------------

        tool_results = []

        for call in function_calls:

            sql = call["arguments"]["sql"]

            # Validation SQL
            valid, message, validated_sql = validate_sql(sql)

            if not valid:

                print("\n=== REQUETE SQL REFUSEE ===")
                print(message)

                tool_output = f"Requête SQL refusée : {message}"

                tool_results.append((call, tool_output))

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

                    action_terminee = True

                else:

                    print("\nExécution annulée.")

                    action_terminee = True

        # --------------------------------------
        # 10. RETOUR DES ERREURS AU LLM
        # --------------------------------------

        if action_terminee:
            break

        response = continue_conversation(
            conversation,
            response,
            tool_results=tool_results
        )
