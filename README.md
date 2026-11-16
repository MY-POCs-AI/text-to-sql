# AI SQL Agent — Text-to-SQL avec RAG

Un agent IA capable de transformer une question formulée en langage naturel en requête SQL, en s'appuyant sur une base documentaire RAG décrivant le schéma d'une base PostgreSQL.

Le projet utilise un LLM pour générer les requêtes, SQLGlot pour les valider et PostgreSQL pour les exécuter après confirmation humaine.

## Fonctionnalités

- Compréhension des questions en langage naturel.
- Recherche du schéma de la base avec ChromaDB.
- Génération de requêtes SQL avec un LLM OpenAI.
- Validation des requêtes avec SQLGlot.
- Contrôle des requêtes avant exécution.
- Confirmation humaine (*Human-in-the-Loop*).
- Exécution SQL avec un compte PostgreSQL en lecture seule.
- Affichage des résultats dans le terminal avec Rich.

## Architecture

```text
Question utilisateur
        |
        v
   RAG / ChromaDB
        |
        v
 Contexte du schéma SQL
        |
        v
    LLM OpenAI
        |
        v
   Génération SQL
        |
        v
 Validation SQLGlot
        |
        v
 Confirmation humaine
        |
        v
 PostgreSQL (lecture seule)
        |
        v
 Affichage des résultats
```

Le RAG indexe les descriptions des tables et les relations entre elles. Il permet au modèle de retrouver les informations nécessaires à la génération des requêtes.

## Technologies

- Python 3.12
- OpenAI API
- ChromaDB
- PostgreSQL 17
- Psycopg 3
- SQLGlot
- Rich
- Docker Compose

## Prérequis

- Python 3.12
- Docker Engine et Docker Compose
- Une clé API OpenAI

**Attention :** l'utilisation de l'API OpenAI est facturée séparément d'un abonnement ChatGPT.

## Installation

### 1. Récupérer le projet

```bash
git clone https://github.com/MY-POCs-AI/text-to-sql.git
cd text-to-sql
```

### 2. Démarrer PostgreSQL

```bash
docker compose up -d
```

La base de démonstration est initialisée automatiquement au premier démarrage, à partir de `init.sql`.

### 3. Créer l'environnement Python

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 5. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Renseigner ensuite sa propre clé API OpenAI dans `.env` :

```env
OPENAI_API_KEY=your_openai_api_key_here
```

Les paramètres PostgreSQL de démonstration sont déjà renseignés dans `.env.example`.

**Ne jamais publier son fichier `.env` ni sa clé API.**

### Changer de fournisseur LLM

Le fournisseur LLM est sélectionné grâce à la variable LLM_PROVIDER dans le fichier .env.

De base il s'agit d'OpenAI.

Les fournisseurs prévus sont :

| Fournisseur | Valeur de `LLM_PROVIDER` | Variable de clé API |
|---|---|---|
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` |
| Google Gemini | `google` | `GOOGLE_API_KEY` |
| Mistral | `mistral` | `MISTRAL_API_KEY` |

Exemple : passer d'OpenAI à Mistral

Modifier le fournisseur dans .env :

```env
LLM_PROVIDER=mistral
```

Renseigner sa clé API Mistral dans .env :

```env
MISTRAL_API_KEY=your_mistral_api_key_here
```

Remarque : chaque fournisseur possède sa propre API et son propre format de gestion des appels d'outils (tool calling). Le changement de valeur de LLM_PROVIDER sélectionne le client correspondant, mais ne suffit pas à garantir la compatibilité de toute la chaîne RAG. L'intégration de chaque fournisseur doit également être réalisée dans la partie communication avec le LLM et traitement des réponses.

## Utilisation

### 1. Indexer le schéma de la base

```bash
python index_schema.py
```

Cette étape récupère les informations du schéma PostgreSQL et les indexe dans ChromaDB.

### 2. Lancer l'agent

```bash
python rag_tool_calling.py
```

Poser ensuite une question en langage naturel.

L'agent génère une requête SQL, la valide puis demande une confirmation avant son exécution.

## Sécurité

Le projet intègre plusieurs mécanismes de protection :

- Validation SQL avec SQLGlot.
- Autorisation des requêtes SELECT uniquement.
- Contrôle des tables accessibles.
- Limitation du nombre de résultats.
- Connexion PostgreSQL avec un utilisateur dédié en lecture seule.
- Confirmation humaine avant exécution.

La base de démonstration et ses identifiants sont destinés exclusivement à un environnement local de test. Ils ne doivent pas être réutilisés en production.

## Base de démonstration

Le script `init.sql` crée un jeu de données fictif comprenant notamment :

- Départements
- Employés
- Clients
- Produits
- Commandes
- Lignes de commandes

Les données permettent de tester des questions impliquant plusieurs tables, des jointures, des agrégations et des filtres.

**Important :** le script d'initialisation Docker ne s'exécute automatiquement que lorsque le volume PostgreSQL est initialisé pour la première fois. Les redémarrages suivants conservent les données existantes.

## Arrêter le projet

```bash
docker compose down
```

Cette commande arrête les conteneurs sans supprimer le volume contenant les données PostgreSQL.

## Sortir de l'environnement python

```bash
deactivate
```

## Objectif du projet

Explorer la conception d'agents IA capables d'interagir avec des systèmes existants, en combinant RAG, génération SQL, validation technique et contrôle humain.

Projet personnel d'expérimentation autour des agents IA et de l'automatisation.