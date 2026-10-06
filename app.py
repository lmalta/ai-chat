from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    Response,
    redirect,
    url_for,
    session
)
from functools import wraps
from werkzeug.security import check_password_hash
import json

from config import Config
from ollama_client import OllamaClient
from stats import build_stats
from conversations import (
    init_db,
    create_conversation,
    add_message,
    get_conversations,
    get_messages,
    conversation_exists,
    get_conversation,
    delete_conversation,
    update_conversation_title,
)
from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename

from document_loader import load_document

app = Flask(__name__)
init_db()
app.config.from_object(Config)

# Configuration session
app.secret_key = Config.SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = Config.SESSION_COOKIE_HTTPONLY
app.config["SESSION_COOKIE_SAMESITE"] = Config.SESSION_COOKIE_SAMESITE
app.config["SESSION_COOKIE_SECURE"] = Config.SESSION_COOKIE_SECURE
app.config["PERMANENT_SESSION_LIFETIME"] = Config.PERMANENT_SESSION_LIFETIME


ollama = OllamaClient(
    Config.OLLAMA_URL,
    Config.OLLAMA_TIMEOUT
)


# ============================================================
# AUTHENTIFICATION
# ============================================================

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if not session.get("authenticated"):
            # Pour les appels API, retourner 401
            if request.path == "/ask":
                return jsonify({
                    "error": "Authentification requise"
                }), 401

            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped_view


@app.route("/login", methods=["GET", "POST"])
def login():

    if session.get("authenticated"):
        return redirect(url_for("index"))

    error = None

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (
            username == Config.AUTH_USERNAME
            and check_password_hash(
                Config.PASSWORD_HASH,
                password
            )
        ):
            session.clear()
            session["authenticated"] = True
            session.permanent = True

            return redirect(url_for("index"))

        error = "Identifiants incorrects"

    return render_template(
        "login.html",
        error=error
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ============================================================
# INTERFACE
# ============================================================

@app.route("/")
@login_required
def index():

    return render_template(
        "index.html",
        models=Config.MODELS,
        default_model=Config.DEFAULT_MODEL
    )


# ============================================================
# HEALTH CHECK
# ============================================================


@app.route("/cancel", methods=["POST"])
@login_required
def cancel_generation():
    cancelled = ollama.cancel()

    return jsonify({
        "cancelled": cancelled
    })


@app.route("/health")
def health():

    return jsonify({
        "status": "ok"
    })

@app.route("/api/conversations")
@login_required
def api_conversations():
    return jsonify(get_conversations())

@app.route("/api/conversations/<int:conversation_id>")
@login_required
def api_get_conversation(conversation_id):

    conversation = get_conversation(conversation_id)

    if conversation is None:
        return jsonify({
            "error": "Conversation introuvable"
        }), 404

    conversation["messages"] = get_messages(conversation_id)

    return jsonify(conversation)

@app.route(
    "/api/conversations/<int:conversation_id>",
    methods=["DELETE"]
)
@login_required
def api_delete_conversation(conversation_id):

    deleted = delete_conversation(
        conversation_id
    )

    if not deleted:
        return jsonify({
            "error": "Conversation introuvable"
        }), 404

    return jsonify({
        "success": True
    })

@app.route(
    "/api/conversations/<int:conversation_id>",
    methods=["PUT"]
)
@login_required
def api_update_conversation(conversation_id):

    data = request.get_json(silent=True) or {}

    title = data.get("title")

    if not isinstance(title, str):
        return jsonify({
            "error": "Titre invalide"
        }), 400

    title = title.strip()

    if not title:
        return jsonify({
            "error": "Le titre ne peut pas être vide"
        }), 400

    if len(title) > 200:
        return jsonify({
            "error": "Titre trop long"
        }), 400

    updated = update_conversation_title(
        conversation_id,
        title
    )

    if not updated:
        return jsonify({
            "error": "Conversation introuvable"
        }), 404

    return jsonify({
        "success": True,
        "title": title
    })

@app.route("/api/conversations", methods=["POST"])
@login_required
def api_create_conversation():

    data = request.get_json(silent=True) or {}

    title = data.get("title", "Nouvelle conversation")

    if not isinstance(title, str):
        return jsonify({
            "error": "Titre invalide"
        }), 400

    title = title.strip()

    if not title:
        title = "Nouvelle conversation"

    if len(title) > 200:
        return jsonify({
            "error": "Titre trop long"
        }), 400

    conversation_id = create_conversation(title)

    return jsonify({
        "id": conversation_id,
        "title": title
    }), 201

# ============================================================
# DOCUMENTS
# ============================================================

DOCUMENT_UPLOAD_DIR = Path("/home/ubuntu/ai-chat/data/documents")

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".xlsx",
}

MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_DOCUMENT_CONTEXT_LENGTH = 30_000

IMAGE_UPLOAD_DIR = Path("/home/ubuntu/ai-chat/data/images")

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

@app.route("/api/documents", methods=["POST"])
@login_required
def upload_document():

    file = request.files.get("file")

    if file is None:
        return jsonify({
            "error": "Aucun fichier fourni"
        }), 400

    if not file.filename:
        return jsonify({
            "error": "Nom de fichier invalide"
        }), 400

    filename = secure_filename(file.filename)

    if not filename:
        return jsonify({
            "error": "Nom de fichier invalide"
        }), 400

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        return jsonify({
            "error": (
                "Format non supporté. "
                "Formats acceptés : PDF, XLSX"
            )
        }), 400

    DOCUMENT_UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    document_id = uuid4().hex

    document_path = (
        DOCUMENT_UPLOAD_DIR
        / f"{document_id}{extension}"
    )

    try:

        file.save(document_path)

        file_size = document_path.stat().st_size

        if file_size > MAX_DOCUMENT_SIZE:
            document_path.unlink(missing_ok=True)

            return jsonify({
                "error": "Fichier trop volumineux. Maximum : 20 MB"
            }), 413

        result = load_document(document_path)

        response = {
            "document_id": document_id,
            "filename": result["filename"],
            "extension": result["extension"],
            "type": result["type"],
            "characters": len(result["text"]),
            "preview": result["text"][:1000],
        }

        if "pages" in result:
            response["pages"] = result["pages"]

        if "sheets" in result:
            response["sheets"] = result["sheets"]

        return jsonify(response), 200

    except Exception as e:

        document_path.unlink(missing_ok=True)

        print(
            f"[DOCUMENT ERROR] "
            f"{type(e).__name__}: {e}"
        )

        return jsonify({
            "error": str(e)
        }), 500

# ============================================================
# IMAGES
# ============================================================

@app.route("/api/images", methods=["POST"])
@login_required
def upload_image():

    file = request.files.get("file")

    if file is None:
        return jsonify({
            "error": "Aucune image fournie"
        }), 400

    if not file.filename:
        return jsonify({
            "error": "Nom de fichier invalide"
        }), 400

    filename = secure_filename(file.filename)

    if not filename:
        return jsonify({
            "error": "Nom de fichier invalide"
        }), 400

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_IMAGE_EXTENSIONS:
        return jsonify({
            "error": (
                "Format non supporté. "
                "Formats acceptés : JPG, JPEG, PNG, WEBP"
            )
        }), 400

    IMAGE_UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    image_id = uuid4().hex

    image_path = (
        IMAGE_UPLOAD_DIR
        / f"{image_id}{extension}"
    )

    try:

        file.save(image_path)

        file_size = image_path.stat().st_size

        if file_size > MAX_IMAGE_SIZE:
            image_path.unlink(missing_ok=True)

            return jsonify({
                "error": "Image trop volumineuse. Maximum : 10 MB"
            }), 413

        return jsonify({
            "image_id": image_id,
            "filename": filename,
            "extension": extension,
        }), 200

    except Exception as e:

        image_path.unlink(missing_ok=True)

        print(
            f"[IMAGE ERROR] "
            f"{type(e).__name__}: {e}"
        )

        return jsonify({
            "error": str(e)
        }), 500

# ============================================================
# CHAT
# ============================================================

@app.route("/ask", methods=["POST"])
@login_required
def ask():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "Requête JSON invalide"
        }), 400

    messages = data.get("messages", [])
    model = data.get(
        "model",
        Config.DEFAULT_MODEL
    )
    conversation_id = data.get("conversation_id")

    document_id = data.get("document_id")

    # Messages destinés à Ollama.
    # On conserve "messages" intact pour les validations
    # et l'historique de conversation.
    ollama_messages = [
        message.copy()
        for message in messages
    ]

    if document_id is not None:

        document_files = list(
            DOCUMENT_UPLOAD_DIR.glob(
                f"{document_id}.*"
            )
        )

        if not document_files:
            return jsonify({
                "error": "Document introuvable"
            }), 404

        document_path = document_files[0]

        try:

            document_result = load_document(
                document_path
            )

            document_text = document_result["text"]

        except Exception as e:

            return jsonify({
                "error": (
                    "Impossible de lire le document : "
                    f"{e}"
                )
            }), 500

        if len(document_text) > MAX_DOCUMENT_CONTEXT_LENGTH:
            return jsonify({
                "error": (
                    "Document trop volumineux pour "
                    "le contexte actuel."
                )
            }), 413

        if (
            ollama_messages
            and ollama_messages[-1].get("role") == "user"
        ):

            user_content = ollama_messages[-1].get(
                "content",
                ""
            )

            ollama_messages[-1]["content"] = (
                "Voici le contenu du document fourni "
                "par l'utilisateur.\n\n"
                "--- DÉBUT DU DOCUMENT ---\n"
                f"{document_text}\n"
                "--- FIN DU DOCUMENT ---\n\n"
                "Réponds à la question de l'utilisateur "
                "en te basant sur ce document.\n\n"
                f"Question de l'utilisateur : "
                f"{user_content}"
            )

    if conversation_id is not None:
        user_message = messages[-1]

        if user_message.get("role") != "user":
            return jsonify({
                "error": "Le dernier message doit être un message utilisateur"
            }), 400

        add_message(
            conversation_id,
            "user",
            user_message.get("content", ""),
            model
        )

        # =========================
        # Validation modèle
        # =========================

        if model not in Config.MODELS:
            return jsonify({
                "error": "Modèle non autorisé"
            }), 400

    # =========================
    # Validation conversation
    # =========================

    if conversation_id is not None:
        if not isinstance(conversation_id, int) or conversation_id <= 0:
            return jsonify({
                "error": "conversation_id invalide"
            }), 400

    if conversation_id is not None:
        if not conversation_exists(conversation_id):
            return jsonify({
                "error": "Conversation introuvable"
            }), 404

    # =========================
    # Validation messages
    # =========================

    if not isinstance(messages, list):
        return jsonify({
            "error": "messages doit être une liste"
        }), 400

    if len(messages) > Config.MAX_MESSAGES:
        return jsonify({
            "error": "Conversation trop longue"
        }), 400

    for message in messages:

        if not isinstance(message, dict):
            return jsonify({
                "error": "Message invalide"
            }), 400

        role = message.get("role")
        content = message.get("content", "")

        if role not in {
            "user",
            "assistant",
            "system"
        }:
            return jsonify({
                "error": "Rôle de message invalide"
            }), 400

        if not isinstance(content, str):
            return jsonify({
                "error": "Contenu de message invalide"
            }), 400

        if len(content) > Config.MAX_MESSAGE_LENGTH:
            return jsonify({
                "error": "Message trop long"
            }), 400

    # =========================
    # Génération streaming
    # =========================

    def generate():
        full_response = []

        try:
            for data in ollama.chat(
                model=model,
                messages=ollama_messages,
                temperature=Config.TEMPERATURE
            ):
                content = data.get("message", {}).get("content", "")

                if content:
                    full_response.append(content)

                    yield json.dumps(
                        {"type": "content", "content": content},
                        ensure_ascii=False
                    ) + "\n"

                if data.get("done"):

                    # =========================
                    # Persistance réponse assistant
                    # =========================

                    if conversation_id is not None:
                        add_message(
                            conversation_id,
                            "assistant",
                            "".join(full_response),
                            model
                        )

                    stats = build_stats(model, data)

                    print(
                        f"[STATS] "
                        f"model={stats['model']} "
                        f"prompt={stats['prompt_tokens']} "
                        f"generated={stats['generated_tokens']} "
                        f"total={stats['total_tokens']} "
                        f"generation={stats['generation_duration']}s "
                        f"total={stats['total_duration']}s "
                        f"tok/s={stats['tokens_per_second']}"
                    )

                    yield json.dumps(
                        stats,
                        ensure_ascii=False
                    ) + "\n"

        except GeneratorExit:
            print("[STOP] Client déconnecté, génération interrompue")

        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {e}")

            yield json.dumps(
                {"type": "error", "error": str(e)},
                ensure_ascii=False
            ) + "\n"

    return Response(
        generate(),
        mimetype="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================
# LANCEMENT LOCAL
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )