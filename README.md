# 🌟 Plateforme Agentic RAG pour l'Analyse Automatisée de Termes de Référence (TdR)

> **Projet de Stage – Architecture IA Souveraine et Confidentielle**
> *Conçu pour EY Global Government & Public Sector Services*

---

## 📝 Présentation du Projet

Dans le cadre des activités de conseil d'**EY**, la réponse aux appels d'offres internationaux nécessite une analyse minutieuse et rapide de cahiers des charges denses, communément appelés **Termes de Référence (TdR)**. 

Ce projet implémente une solution de **RAG Avancé (Retrieval-Augmented Generation)** et **Agentique** permettant :
1. **L'ingestion automatisée** de volumes massifs de TdR au format PDF.
2. **La recherche sémantique bidirectionnelle** pour identifier instantanément les critères d'éligibilité, les grilles de notation et les profils d'experts requis.
3. **La génération de synthèses décisionnelles** fiables et structurées à l'aide d'un grand modèle de langage (LLM) exécuté localement.

**🔒 Souveraineté & Confidentialité :** Pour respecter le secret professionnel et la gouvernance des données d'EY, l'intégralité de cette architecture (base vectorielle, pipeline d'extraction, embeddings et LLM) s'exécute **à 100 % localement (On-Premise)**. Aucune donnée ne transite par des API tierces.

---

## 🏗️ Architecture Technique Fondamentale

L'application est découpée en micro-services et composants hautement découplés :

   [ Interface Utilisateur React (Vite) ]
                     │
                     ▼ (Requêtes REST Asynchrones)
         [ API Backend FastAPI ]
                     │
     ┌───────────────┴───────────────┐
     ▼                               ▼
[ Base Vectorielle Qdrant ]    [ Moteur Local Ollama ]
(Indexation Child Chunks)      (Llama 3.2:3b Inférence)
│                               │
▼                               ▼
[ Local Parent Store ]         [ Orchestrateur LangGraph ]
(Restauration Contexte Riche)     (Boucles de Contrôle / Self-RAG)


### 1. Ingestion & Stratégie Avancée "Parent/Child Chunking"
Le RAG traditionnel souffre d'un dilemme : des morceaux de texte trop petits dégradent la compréhension du LLM (perte de contexte), tandis que des morceaux trop grands diluent le signal sémantique dans la base vectorielle. 
Pour résoudre ce problème, ce projet implémente une approche **Parent/Child** :
* **Child Chunks (200 à 400 tokens) :** Les documents sont segmentés finement, vectorisés avec le modèle `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) et stockés dans **Qdrant**. C'est sur ces fragments que s'effectue la recherche mathématique de similarité.
* **Parent Chunks (1000 à 1500 tokens) :** Lorsqu'un *Child Chunk* est sélectionné par Qdrant, le backend intercepte son ID et remonte le *Parent Chunk* complet (le paragraphe ou la page entière correspondante) stocké dans un store local au format JSON. C'est ce contexte enrichi qui est envoyé au LLM.

### 2. Orchestration Agentique (LangGraph)
L'onglet **RAG Agentic** utilise **LangGraph** pour briser la linéarité du RAG classique (Question ➔ Recherche ➔ Réponse). Il introduit un comportement adaptatif :
* **Self-RAG (Boucle de rétroaction) :** L'agent utilise le LLM pour évaluer si les documents extraits par Qdrant sont pertinents vis-à-vis de la question.
* **Pivot Contextuel :** Si la base documentaire locale ne contient pas l'information (par exemple, si un document est manquant ou hors-sujet), l'agent le détecte, notifie explicitement l'utilisateur, et bascule de manière sécurisée sur les connaissances générales du modèle pour fournir un cadre méthodologique ou théorique plutôt que de générer une hallucination.

### 3. Frontend d'Analyse Métier (React)
L'interface utilisateur a été conçue pour offrir une expérience fluide, calquée sur les standards visuels d'EY :
* **Filtres Facettés Dynamiques :** Analyse en temps réel des métadonnées des documents retournés pour permettre un filtrage chirurgical par **Domaine** (Audit, Juridique, IT...), **Pays** (RDC, Mali, Mauritanie...) et **Année**.
* **Indicateurs de Confiance :** Restitution visuelle des scores de similarité sémantique issus de Qdrant sous forme de barres de progression horizontales colorées.

---

## 🛠️ Résolution des Problématiques d'Ingestion (Bugfixes Bas Niveau)

Lors de la phase de test sur des TdR réels (notamment les formats complexes de missions d'appui), deux anomalies majeures d'extraction de données ont été identifiées et corrigées dans le module `ingest.py` :
1. **Le problème de fusion des mots (Espaces absents) :** Les polices de caractères de certains documents officiels provoquaient une extraction linéaire brute collant les mots entre eux (ex: *`importantsdesbailleurs`*). Ce phénomène rendait les mots invisibles pour l'embedder. Le code a été migré vers l'**`extraction_mode="layout"`** de `pypdf`, préservant la géométrie physique des espaces.
2. **Le piège des octets nuls (`\u0000`) :** Les ligatures typographiques complexes (comme le sous-ensemble de caractères pour *`ffi`* dans *efficacement*) généraient des caractères nuls provoquant des troncatures de chaînes lors du transfert vers la base de données. Un nettoyage par expressions régulières (Regex) a été intégré pour normaliser le flux textuel avant vectorisation.

---

## 🚀 Manuel de Déploiement Local

### Prérequis Système
* **Python 3.11 ou supérieur**
* **Node.js v20+ / npm**
* **Ollama** installé sur la machine hôte avec le modèle Llama 3.2 téléchargé (`ollama run llama3.2`).

### 1. Configuration et Lancement du Backend
Ouvre une invite de commande dans le sous-dossier `backend` :
```cmd
# Activation de l'environnement isolé
python -m venv venv
venv\Scripts\activate

# Installation des dépendances (FastAPI, Qdrant-Client, LangGraph, PyPDF, Sentence-Transformers)
pip install -r requirements.txt

# Étape A : Extraction et nettoyage géométrique des PDF (génère les fichiers .txt)
python -m app.ingest

# Étape B : Chunking Parent/Child, vectorisation et initialisation de la collection Qdrant
python -m app.indexing --reset

# Étape C : Lancement du serveur d'API
cd ..
python -m uvicorn backend.app.main:app --reload --port 8000
2. Configuration et Lancement du Frontend
Ouvre un second terminal dans le sous-dossier frontend :

DOS
# Installation des packages Node (React, Vite, TailwindCSS, Lucide Icons)
npm install

# Lancement du serveur de développement local
npm run dev
L'application est alors accessible dans ton navigateur sur : http://localhost:5173/

🐳 Conteneurisation de Production (Docker Compose)
Pour déployer l'architecture de manière industrielle et isolée, un fichier docker-compose.yml orchestre trois conteneurs distincts :

qdrant : Le serveur de base de données vectorielle officiel (persistance des données sur volume local).

backend : L'API FastAPI (Python 3.11-slim).

frontend : Le serveur de distribution React (Node v20-alpine).

Pour construire et démarrer l'ensemble de la grille de services, exécute la commande suivante à la racine du projet :

Bash
docker compose up --build
Note d'infrastructure : Afin d'éviter la surcharge de mémoire RAM dans les conteneurs, le service backend est configuré via la variable d'environnement OLLAMA_HOST=http://host.docker.internal:11434 pour solliciter directement le moteur Ollama installé nativement sur le système d'exploitation hôte.

📊 Matrice des Scénarios de Validation (Soutenance)
Pour valider le comportement du système lors de l'évaluation, l'application permet de tester trois paradigmes de recherche :

Le Moteur Vectoriel (Vérification de l'indexation) : Interroge directement la base de données Qdrant. Permet de valider la justesse du modèle d'embedding et de vérifier l'extraction des documents (ex: chercher "Bluesquare" ou "Règlement de passation des marchés" pour voir les scores remonter au-dessus de 65%).

Le RAG Simple (Analyse Linéaire) : Utile pour l'extraction factuelle directe lorsque la question correspond précisément au contenu d'un document maître.

Le RAG Agentic (Boucle de Contrôle LangGraph) : Démontre la capacité de l'IA à analyser de manière critique les données d'entreprise, à rejeter les documents hors-sujet et à fournir un support méthodologique sans hallucination.
