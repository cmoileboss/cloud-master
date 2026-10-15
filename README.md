# FFK — Assistant du Service des Grades

Prototype d'application pour le secrétariat du Service des Grades d'une fédération de karaté. Il fonctionne
en local. Votre travail consistera à le connecter à un fournisseur LLM, puis à le mettre en ligne (voir
les briefs sur la plateforme).

L'utilisateur décrit la convocation souhaitée en une phrase (« la prochaine réunion de la CSDGE »). L'IA
retrouve la réunion dans le calendrier et rédige l'introduction ; le backend produit un PDF, l'enregistre
et l'ajoute à la liste des convocations générées.

Toutes les données sont fictives.

## Architecture

```text
                       ┌────────────────────────┐
Navigateur ──────────► │ frontend  (React/Vite) │  http://localhost:5173
    │                  └────────────────────────┘
    │  appels API (VITE_API_URL)
    ▼
┌────────────────────┐      ┌──────────────────────────────┐
│ backend  (FastAPI) │ ───► │ PostgreSQL (Docker) :        │  localhost:5432
│ localhost:8000     │      │ liste des convocations       │
│                    │      └──────────────────────────────┘
│                    │ ───► dossier backend/data/documents/ : fichiers PDF
│                    │ ───► fournisseur LLM (à configurer)
└────────────────────┘
```

- Le navigateur charge l'interface depuis le **frontend**, puis appelle **directement** le backend.
  L'adresse du backend est fixée **à la compilation** du frontend par `VITE_API_URL`.
- Le backend n'accepte que les origines listées dans `CORS_ORIGINS`.
- Les secrets (base de données, LLM, stockage) restent côté backend. Le frontend n'en contient aucun.

## Installation

Prérequis : Python 3.11+, Node 22.12+ et Docker Desktop (uniquement pour PostgreSQL). Depuis ce dossier, une
première fois :

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"
npm ci --prefix frontend
```

## Démarrage

Trois terminaux, depuis ce dossier :

```powershell
docker compose up -d                                                  # 1. PostgreSQL
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend   # 2. backend
npm run dev --prefix frontend                                         # 3. frontend
```

Ouvrir http://localhost:5173. La documentation interactive de l'API est sur http://localhost:8000/docs.
Les logs du backend s'affichent dans son terminal.

Le backend et le frontend lisent tous les deux le `.env` à la racine. Après une modification, redémarrez
le backend (Ctrl+C puis relancer) ; le serveur de développement du frontend se recharge seul.

Sans fournisseur LLM, l'interface et le calendrier s'affichent ; la génération répond « LLM non
configuré ». Pour le configurer : voir [Connecter un fournisseur LLM](#connecter-un-fournisseur-llm).

Pour arrêter PostgreSQL : `docker compose down`. Pour l'arrêter **et effacer ses données** :
`docker compose down -v`.

## Configuration

Le backend lit ses paramètres dans les variables d'environnement, puis dans le fichier `.env` à la
racine (voir `backend/app/config.py`). Le frontend lit `VITE_API_URL` au même endroit (voir
`frontend/vite.config.ts`). Sur une plateforme d'hébergement, on les renseigne dans les paramètres du
service.

| Variable            | Lue par         | Rôle                                                                                    |
| ------------------- | --------------- | --------------------------------------------------------------------------------------- |
| `DATABASE_URL`      | backend         | Connexion PostgreSQL, au format `postgresql+psycopg://utilisateur:motdepasse@hôte:5432/base` |
| `CORS_ORIGINS`      | backend         | Origines du frontend autorisées, séparées par des virgules (protocole + domaine + port)  |
| `LLM_BASE_URL`      | backend         | Adresse de l'API du fournisseur LLM                                                      |
| `LLM_MODEL`         | backend         | Identifiant du modèle                                                                    |
| `LLM_API_KEY`       | backend         | Clé personnelle (secrète)                                                                |
| `DATA_DIR`          | backend         | Dossier des PDF locaux (défaut : `backend/data`)                                         |
| `VITE_API_URL`      | frontend        | Adresse publique du backend, **intégrée à la compilation**                               |
| `POSTGRES_*`        | Docker (`db`)   | Utilisateur, mot de passe et base du PostgreSQL local                                    |

### Relier le frontend et le backend

Le frontend est un ensemble de fichiers statiques : il ne lit aucune variable au moment où il est servi.
`VITE_API_URL` est remplacée par sa valeur pendant `npm run build`, qui produit le dossier
`frontend/dist`. Changer la variable impose donc de **recompiler et redéployer** le frontend. Cette valeur
est publique : elle ne doit contenir aucun secret.

Côté backend, `CORS_ORIGINS` doit contenir l'origine exacte du frontend, par exemple
`https://mon-frontend.example`, sans chemin. Sinon le navigateur bloque les réponses et l'interface
affiche « Backend injoignable ».

### Connecter un fournisseur LLM

Le backend utilise le SDK `openai` avec une adresse configurable. Il fonctionne avec tout fournisseur qui
propose une API **compatible OpenAI « chat/completions »** et le **mode JSON**
(`response_format: {"type": "json_object"}`). Vérifiez ces deux points dans la documentation du
fournisseur et du modèle choisis.

```dotenv
LLM_BASE_URL=adresse-de-l-api-indiquée-par-le-fournisseur
LLM_MODEL=identifiant-du-modèle
LLM_API_KEY=votre-clé
```

`LLM_BASE_URL` est la racine de l'API, en général terminée par `/v1` : le SDK y ajoute lui-même
`/chat/completions`. Ne copiez pas l'adresse complète de l'endpoint.

Puis redémarrez le backend et générez une convocation.

Chaque appel envoie le prompt de `backend/prompts/preparer-convocation.md`, le schéma JSON attendu,
la demande et le calendrier. La réponse est validée avec Pydantic avant utilisation. Une réponse JSON
valide n'est pas forcément pertinente : vérifiez la réunion choisie et le texte rédigé.

En cas d'échec, l'interface indique la variable à vérifier ; les logs du backend contiennent le détail
renvoyé par le fournisseur :

```text
INFO  ffk.llm: llm_ok prompt=preparer-convocation model=... duration=1.8s
ERROR ffk.llm: llm_failed prompt=preparer-convocation model=... error=AuthenticationError detail=...
ERROR ffk.llm: llm_invalid_output prompt=preparer-convocation model=... output='...'
```

Vérifiez le coût du modèle et les quotas de l'offre, et fixez un plafond de dépenses.

## Organisation du code

| Fichier                               | Rôle                                                        |
| ------------------------------------- | ----------------------------------------------------------- |
| `backend/app/main.py`                 | Assemble l'application : services, CORS, routes             |
| `backend/app/routes/documents.py`     | Routes du calendrier et des convocations                    |
| `backend/app/routes/health.py`        | Sondes de santé pour l'hébergeur                            |
| `backend/app/llm.py`                  | Appel au fournisseur LLM et traduction de ses erreurs       |
| `backend/app/storage.py`              | Lecture et écriture des PDF (dossier local)                 |
| `backend/app/models.py`               | Tables de la base et formats de données                     |
| `backend/app/config.py`               | Paramètres lus dans l'environnement                         |
| `backend/app/meetings.py`             | Calendrier fictif (dates calculées depuis aujourd'hui)      |
| `backend/app/pdf.py`                  | Mise en page du PDF                                         |
| `backend/prompts/`                    | Prompt envoyé au LLM, modifiable sans toucher au code       |
| `backend/fixtures/meetings.json`      | Réunions fictives                                           |
| `backend/tests/`                      | Tests automatisés (aucun appel réseau)                      |
| `frontend/src/api.ts`                 | Appels au backend et messages d'erreur                      |
| `frontend/src/documents/`             | Écran des convocations : demande, aperçu, historique        |

## Routes de l'API

| Méthode | Chemin                              | Rôle                                         |
| ------- | ----------------------------------- | -------------------------------------------- |
| GET     | `/health/live`                      | Le processus répond                          |
| GET     | `/health/ready`                     | La base de données répond                    |
| GET     | `/api/meetings`                     | Calendrier fictif                            |
| POST    | `/api/documents/generate`           | Génère une convocation à partir d'une demande |
| GET     | `/api/documents`                    | Convocations déjà générées                   |
| GET     | `/api/documents/{id}/download`      | Télécharge le PDF                            |

## Tests et vérifications

```powershell
.\.venv\Scripts\python.exe -m pytest backend          # tests du backend
.\.venv\Scripts\python.exe -m ruff check backend      # qualité du code Python
.\.venv\Scripts\python.exe -m ruff format --check backend   # mise en forme du code Python
npm run build --prefix frontend                       # compilation du frontend (dossier frontend/dist)
npm run format:check --prefix frontend                # mise en forme du frontend
```

Les tests utilisent SQLite et un faux LLM : ils n'ont besoin ni de PostgreSQL, ni de clé.

## Points d'adaptation pour un déploiement

- **Lancement du backend** : installer `backend/requirements.lock`, puis lancer depuis le dossier
  `backend` : `uvicorn app.main:app --host 0.0.0.0 --port <port imposé par l'hébergeur>`. Les dossiers
  `prompts/` et `fixtures/` doivent être déployés avec `app/`.
- **Frontend** : le contenu de `frontend/dist` (après `npm run build`) est un site statique.
- **Stockage des PDF** : `backend/app/storage.py` écrit dans un dossier local, qui disparaît à chaque
  redéploiement ou redémarrage sur la plupart des hébergements. Une autre classe avec les mêmes méthodes
  `put(key, content)` et `get(key)` peut la remplacer : il suffit de changer l'instanciation dans
  `create_app` (`backend/app/main.py`). La liste des convocations est en base ; seul le fichier est dans
  le stockage.
- **Base de données** : les tables sont créées au démarrage si elles n'existent pas (`init_db`). Une
  table existante n'est jamais modifiée.
- **Sondes de santé** : `/health/live` (le processus répond) et `/health/ready` (la base répond).
- **Logs** : le backend écrit sur la sortie standard. Les événements utiles au diagnostic sont
  `llm_ok`, `llm_failed`, `llm_invalid_output`, `storage_put_failed` et `storage_get_failed`.

## Calendrier fictif

`backend/fixtures/meetings.json` décrit les réunions avec un délai (`in_days`) plutôt qu'une date. Les
dates sont calculées à partir d'aujourd'hui (et décalées au lundi si elles tombent un week-end). Le
calendrier reste donc dans le futur quelle que soit la date de la session.
