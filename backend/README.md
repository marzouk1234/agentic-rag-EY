# 🌟 Agentic RAG - Plateforme d'Analyse de Termes de Référence (TdR)

> **Projet de Fin d'Études / Stage – Architecture IA Souveraine pour EY Global Government & Public Sector Services**

Ce dépôt unique rassemble l'architecture logicielle complète d'un système de **RAG Avancé (Retrieval-Augmented Generation)** et **Agentique**. Conçu pour automatiser l'analyse, la classification et l'extraction de critères critiques au sein d'appels d'offres et de Termes de Référence internationaux, le système s'exécute **à 100 % localement** afin de garantir la souveraineté et la confidentialité absolue des données.

---

## 🏗️ Architecture Globale du Système

L'application est structurée en deux composants principaux orchestrés de manière transparente :

### 1. Le Backend (FastAPI & LangGraph)
* **Framework :** FastAPI pour une gestion asynchrone performante des requêtes.
* **Orchestration Agentique :** **LangGraph** implémente un circuit de décision intelligent (*Self-RAG*). L'agent évalue la pertinence du contexte extrait et peut décider de reformuler la requête ou de solliciter la culture générale du modèle si les documents locaux sont hors-sujet.
* **Stratégie d'Indexation (Parent/Child) :** Découpage des documents en *Child Chunks* sémantiques fins (200-400 tokens) pour maximiser la précision de la recherche vectorielle, associés à des *Parent Chunks* structurels (1000-1500 tokens) envoyés au LLM pour conserver un contexte riche et éviter la dilution sémantique.
* **Modèles Locaux :** Embeddings générés via `sentence-transformers/all-MiniLM-L6-v2` et inférence de texte via **Ollama (Llama 3.2:3b)**.

### 2. Le Frontend (React & Vite)
* **Interface Utilisateur :** UI réactive développée en React, respectant le Design System et la charte graphique d'EY (Noir, Jaune, Blanc, Gris).
* **Filtres Dynamiques :** Module d'analyse de métadonnées permettant de filtrer les résultats en temps réel par **Domaine** (Audit, Finance, IT...), **Pays** (RDC, Mali, Mauritanie...) et **Année**.
* **Visualisation :** Restitution claire des scores de similarité vectorielle calculés par Qdrant sous forme de barres de progression dynamiques.

---

## 🛠️ Pipeline de Traitement des Données & Résolution de Bugs

Le moteur d'ingestion intègre des correctifs bas niveau essentiels pour la robustesse du traitement des PDFs complexes :
* **Extraction en Mode Layout :** Configuration de l'extraction géométrique via `pypdf` pour éliminer le problème des mots collés (fusion d'espaces) provoqués par les polices de caractères d'appels d'offres.
* **Nettoyage des Octets Nuls :** Suppression automatisée des caractères de fin de chaîne `\u0000` générés par les ligatures complexes (ex: *ffi*), évitant le masquage ou la troncature des données lors du chargement dans la base vectorielle.

---

## 🚀 Guide de Démarrage Rapide

### Prérequis
* Python 3.11+
* Node.js (v20+)
* Ollama installé en local avec le modèle récupéré : `ollama run llama3.2`

### 1. Configuration et Lancement du Backend
Ouvrez un terminal dans le répertoire racine du projet :
```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Phase 1 : Ingestion du texte brut des PDF
python -m app.ingest

# Phase 2 : Découpage Parent/Child et indexation dans la collection Qdrant
python -m app.indexing --reset

# Lancement de l'API FastAPI
cd ..
python -m uvicorn backend.app.main:app --reload --port 8000