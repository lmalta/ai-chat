# 🤖 Mon IA locale

Application web de chat IA locale basée sur **Flask** et **Ollama**.

L'application permet d'utiliser des modèles de langage exécutés localement, avec une interface web, un historique des conversations, le streaming des réponses et l'affichage des statistiques de génération.

Aucune API cloud n'est nécessaire pour générer les réponses : les modèles sont fournis par une instance Ollama accessible par l'application.

## ✨ Fonctionnalités

* 💬 Interface web de chat
* 🧠 Sélection du modèle IA
* ⚡ Réponses générées en streaming
* 🛑 Arrêt d'une génération en cours
* 📚 Historique des conversations
* ✏️ Renommage des conversations
* 🗑️ Suppression des conversations
* 📝 Persistance des conversations dans une base SQLite locale
* 📊 Statistiques de génération
* 🔐 Authentification par identifiant et mot de passe
* 🍪 Sessions sécurisées côté serveur
* 📝 Rendu Markdown des réponses
* 💻 Interface adaptée aux écrans desktop et mobiles
* 🔌 API HTTP interne pour les conversations et la génération

## 🧠 Modèles

Les modèles autorisés sont actuellement :

* `qwen3:8b`
* `qwen3:14b`

Les modèles sont exécutés par **Ollama**.

La liste des modèles autorisés peut être modifiée dans `config.py`.

## 📊 Statistiques

Après chaque génération, l'application peut récupérer et afficher les statistiques fournies par Ollama, notamment :

* modèle utilisé
* nombre de tokens du prompt
* nombre de tokens générés
* nombre total de tokens
* durée de génération
* durée totale
* vitesse de génération en tokens/seconde

Ces informations sont également journalisées côté serveur.

## 🛠️ Architecture

```text
ai-chat/
├── app.py
├── config.py
├── conversations.py
├── ollama_client.py
├── stats.py
├── requirements.txt
│
├── static/
│   ├── app.js
│   └── style.css
│
└── templates/
    ├── index.html
    └── login.html
```

### Principaux composants

**`app.py`**

Application Flask principale.

Elle gère notamment :

* authentification
* interface web
* API des conversations
* génération des réponses
* streaming NDJSON
* arrêt d'une génération
* health check

**`ollama_client.py`**

Client utilisé pour communiquer avec l'API Ollama.

**`conversations.py`**

Gestion de la persistance des conversations et des messages dans SQLite.

**`stats.py`**

Construction des statistiques de génération à partir des données retournées par Ollama.

**`config.py`**

Configuration de l'application et chargement des variables d'environnement.

**`static/`**

JavaScript et CSS de l'interface.

**`templates/`**

Templates HTML Flask.

## 📋 Prérequis

* Python 3.10 ou supérieur
* Ollama
* Au moins un modèle compatible installé dans Ollama
* Git

Pour vérifier Ollama :

```bash
ollama --version
```

Pour vérifier les modèles disponibles :

```bash
ollama list
```

Par exemple :

```bash
ollama pull qwen3:8b
ollama pull qwen3:14b
```

## 🚀 Installation

Cloner le projet :

```bash
git clone https://github.com/lmalta/ai-chat.git
cd ai-chat
```

Créer un environnement virtuel :

```bash
python3 -m venv .venv
```

Activer l'environnement :

```bash
source .venv/bin/activate
```

Installer les dépendances :

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

L'application utilise un fichier `.env` à la racine du projet.

Créer le fichier :

```bash
nano .env
```

Exemple :

```env
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_TIMEOUT=600

DEFAULT_MODEL=qwen3:14b
TEMPERATURE=0.7

MAX_MESSAGE_LENGTH=10000
MAX_MESSAGES=50

AUTH_USERNAME=admin
SECRET_KEY=change-me
PASSWORD_HASH=change-me
```

### Authentification

L'application nécessite :

* `AUTH_USERNAME`
* `PASSWORD_HASH`
* `SECRET_KEY`

Le mot de passe n'est pas stocké en clair : l'application utilise un hash compatible avec Werkzeug.

Pour générer un hash de mot de passe :

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('VotreMotDePasse'))"
```

Copier ensuite le résultat dans :

```env
PASSWORD_HASH=...
```

### Sécurité du fichier `.env`

Le fichier `.env` contient des informations sensibles et **ne doit jamais être commité dans Git**.

Le `.gitignore` fourni avec le projet l'exclut déjà.

## ▶️ Lancement

Pour lancer l'application directement avec Flask :

```bash
python app.py
```

L'application écoute alors sur :

```text
http://localhost:8080
```

Pour une utilisation avec Gunicorn :

```bash
gunicorn --bind 0.0.0.0:8080 app:app
```

Pour un environnement de production, il est recommandé d'utiliser un gestionnaire de service comme `systemd` ou un reverse proxy.

## 🔄 Communication avec Ollama

L'application communique avec Ollama via son API HTTP.

Le flux de génération est :

```text
Navigateur
    │
    ▼
Flask
    │
    ▼
Ollama
    │
    ▼
Modèle local
    │
    ▼
Streaming de la réponse
    │
    ▼
Navigateur
```

Les réponses sont transmises progressivement au navigateur afin d'éviter d'attendre la fin complète de la génération.

## 🗂️ Conversations

Les conversations sont stockées localement dans une base SQLite.

L'application permet :

* de créer une conversation
* de charger une conversation existante
* de renommer une conversation
* de supprimer une conversation
* de conserver les messages utilisateur et assistant

La base de données locale n'est pas destinée à être versionnée dans Git.

## 🔌 API

Quelques endpoints utilisés par l'application :

| Méthode  | Endpoint                  | Fonction                                |
| -------- | ------------------------- | --------------------------------------- |
| `GET`    | `/`                       | Interface principale                    |
| `GET`    | `/login`                  | Page de connexion                       |
| `POST`   | `/login`                  | Authentification                        |
| `GET`    | `/logout`                 | Déconnexion                             |
| `GET`    | `/health`                 | Vérification de l'état de l'application |
| `POST`   | `/ask`                    | Génération d'une réponse                |
| `POST`   | `/cancel`                 | Arrêt d'une génération                  |
| `GET`    | `/api/conversations`      | Liste des conversations                 |
| `POST`   | `/api/conversations`      | Création d'une conversation             |
| `GET`    | `/api/conversations/<id>` | Lecture d'une conversation              |
| `PUT`    | `/api/conversations/<id>` | Renommage                               |
| `DELETE` | `/api/conversations/<id>` | Suppression                             |

## 🔒 Sécurité

Quelques mesures sont intégrées à l'application :

* authentification obligatoire pour l'interface et les API protégées
* mot de passe stocké sous forme de hash
* clé secrète Flask fournie par variable d'environnement
* cookies de session `HttpOnly`
* cookies de session avec `SameSite=Lax`
* validation des modèles autorisés
* validation des messages reçus par l'API
* limitation de la taille des messages
* limitation du nombre de messages envoyés dans une conversation

### Déploiement public

Cette application est conçue pour fonctionner avec un modèle local, mais **cela ne signifie pas que l'interface web doit être exposée directement sur Internet**.

Pour un déploiement accessible depuis Internet, il est recommandé de mettre en place au minimum :

* HTTPS
* un reverse proxy
* une politique firewall adaptée
* des identifiants robustes
* une gestion correcte des secrets
* une limitation d'accès réseau lorsque cela est possible

## 🧪 Développement

L'application peut être lancée directement avec Flask pendant le développement :

```bash
python app.py
```

Pour tester la syntaxe Python :

```bash
python -m py_compile app.py
```

Pour installer les dépendances de développement :

```bash
pip install -r requirements.txt
```

## 📦 Dépendances principales

Le projet utilise notamment :

* [Flask](https://flask.palletsprojects.com/)
* [Requests](https://requests.readthedocs.io/)
* [Gunicorn](https://gunicorn.org/)
* [python-dotenv](https://github.com/theskumar/python-dotenv)
* [Ollama](https://ollama.com/)

## 🗺️ Roadmap

Quelques pistes d'évolution possibles :

* amélioration continue de l'interface
* gestion plus avancée des paramètres de génération
* support de modèles supplémentaires
* amélioration de la gestion des conversations
* meilleure gestion du déploiement sécurisé
* ajout éventuel de fonctionnalités d'agent IA

La roadmap peut évoluer avec le projet.

## 📄 Licence

Aucune licence open source n'est actuellement déclarée dans ce dépôt.

Si le projet est rendu public, une licence peut être ajoutée selon les conditions d'utilisation souhaitées par le mainteneur.

---

## 🤝 Contribution

Les contributions, suggestions et retours sont les bienvenus.

Pour proposer une modification importante, il est recommandé d'ouvrir une issue afin de discuter de l'évolution avant de soumettre une pull request.
