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

    # =========================
    # Validation modèle
    # =========================

    if model not in Config.MODELS:
        return jsonify({
            "error": "Modèle non autorisé"
        }), 400

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

        try:

            for data in ollama.chat(
                model=model,
                messages=messages,
                temperature=Config.TEMPERATURE
            ):

                # -------------------------
                # Texte généré
                # -------------------------

                content = data.get(
                    "message",
                    {}
                ).get(
                    "content",
                    ""
                )

                if content:

                    yield json.dumps(
                        {
                            "type": "content",
                            "content": content
                        },
                        ensure_ascii=False
                    ) + "\n"

                # -------------------------
                # Fin de génération
                # -------------------------

                if data.get("done"):

                    stats = build_stats(
                        model,
                        data
                    )

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

            print(
                f"[ERROR] {type(e).__name__}: {e}"
            )

            yield json.dumps(
                {
                    "type": "error",
                    "error": str(e)
                },
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