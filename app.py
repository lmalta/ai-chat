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
)

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
                messages=messages,
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