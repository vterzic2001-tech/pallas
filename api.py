# api.py
import os
from functools import wraps

from dotenv import load_dotenv
from flask import (Flask, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

import storage
from coach_agent import explain_answer, generate_task

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

storage.init_db()
storage.seed_db()

if not os.getenv("DEEPSEEK_API_KEY"):
    print("WARNING: DEEPSEEK_API_KEY not set. Task generation will fail.")


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "auth_required"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or len(password) < 6:
        return jsonify({"error": "Email and password (min 6 chars) required"}), 400
    uid = storage.create_user(email, generate_password_hash(password))
    if uid is None:
        return jsonify({"error": "Email already registered"}), 409
    session["user_id"] = uid
    return jsonify({"ok": True})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = storage.get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401
    session["user_id"] = user["id"]
    return jsonify({"ok": True})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/me")
@login_required
def api_me():
    u = storage.get_user_by_id(session["user_id"])
    return jsonify({"email": u["email"]})


@app.route("/api/task/new")
@login_required
def api_task_new():
    category = request.args.get("category", "sequences")
    try:
        difficulty = int(request.args.get("difficulty", 3))
    except ValueError:
        difficulty = 3
    difficulty = max(1, min(5, difficulty))
    if category not in ("sequences", "analogies", "matrices"):
        return jsonify({"error": "Unknown category"}), 400

    user_id = session["user_id"]
    prev = storage.get_last_stem(user_id, category)

    try:
        task = generate_task(category, difficulty, previous_stem=prev)
    except Exception as e:
        return jsonify({"error": f"Task generation failed: {e}"}), 500

    task_id = storage.save_task(user_id, task)
    return jsonify({
        "id": task_id,
        "category": task["category"],
        "difficulty": task["difficulty"],
        "stem": task["stem"],
        "options": task["options"],
    })


@app.route("/api/task/answer", methods=["POST"])
@login_required
def api_task_answer():
    data = request.get_json() or {}
    try:
        task_id = int(data.get("task_id"))
        user_index = int(data.get("user_index"))
        time_ms = int(data.get("time_ms", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid payload"}), 400
    if not (0 <= user_index <= 3):
        return jsonify({"error": "user_index out of range"}), 400

    task = storage.get_task_by_id(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    is_correct = (user_index == task["correct_index"])

    try:
        explanation = explain_answer(task, user_index)
    except Exception as e:
        explanation = f"(Explanation unavailable: {e})"

    storage.save_attempt(
        user_id=session["user_id"],
        task_id=task_id,
        category=task["category"],
        difficulty=task["difficulty"],
        user_index=user_index,
        correct_index=task["correct_index"],
        is_correct=is_correct,
        time_ms=time_ms,
        explanation=explanation,
    )

    why_wrong = ""
    if not is_correct:
        why_wrong = task.get("why_wrong", {}).get(str(user_index), "")

    return jsonify({
        "is_correct": is_correct,
        "correct_index": task["correct_index"],
        "rule": task["rule"],
        "explanation": explanation,
        "why_wrong": why_wrong,
    })



@app.route("/api/test/compare", methods=["POST"])
@login_required
def api_test_compare():
    data = request.get_json() or {}
    task_ids = data.get("task_ids", [])
    user_score = data.get("user_score", 0)
    user_time_ms = data.get("user_time_ms", 0)
    
    total = len(task_ids)
    if total == 0:
        return jsonify({"error": "No tasks provided"}), 400

    # PALLAS uvijek ima 100% jer je on kreirao i verificirao zadatke.
    pallas_score = total
    # Simuliramo PALLAS-ovo vrijeme: ~1.5s po zadatku (generiranje + verifikacija)
    pallas_time_ms = total * 1500 

    return jsonify({
        "user": {"score": user_score, "total": total, "time_ms": user_time_ms},
        "pallas": {"score": pallas_score, "total": total, "time_ms": pallas_time_ms}
    })

@app.route("/api/progress")
@login_required
def api_progress():
    uid = session["user_id"]
    return jsonify({
        "progress": storage.get_progress(uid),
        "days_practiced": storage.get_days_practiced(uid),
    })



@app.route('/service-worker.js')
def sw():
    return app.send_static_file('service-worker.js')

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000, debug=True)
