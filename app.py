from datetime import date, datetime
import sqlite3

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)
DATABASE = "tasks.db"
VALID_STATUSES = {"todo", "in_progress", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'todo',
                priority TEXT NOT NULL DEFAULT 'medium',
                due_date TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        task_count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if task_count == 0:
            connection.executemany(
                """
                INSERT INTO tasks (title, description, status, priority, due_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "Map the first user journey",
                        "Sketch the smallest useful path through the product.",
                        "in_progress",
                        "high",
                        date.today().isoformat(),
                        datetime.utcnow().isoformat(timespec="seconds"),
                    ),
                    (
                        "Set up API error handling",
                        "Return consistent JSON errors for invalid requests.",
                        "todo",
                        "medium",
                        None,
                        datetime.utcnow().isoformat(timespec="seconds"),
                    ),
                    (
                        "Ship a tiny victory",
                        "Complete one small task and make the progress visible.",
                        "done",
                        "low",
                        None,
                        datetime.utcnow().isoformat(timespec="seconds"),
                    ),
                ],
            )


def serialize_task(task):
    return dict(task)


def validate_task_payload(payload, partial=False):
    errors = {}
    if not partial or "title" in payload:
        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            errors["title"] = "A title is required."
    if "status" in payload and payload["status"] not in VALID_STATUSES:
        errors["status"] = "Status must be todo, in_progress, or done."
    if "priority" in payload and payload["priority"] not in VALID_PRIORITIES:
        errors["priority"] = "Priority must be low, medium, or high."
    if "due_date" in payload and payload["due_date"]:
        try:
            date.fromisoformat(payload["due_date"])
        except (TypeError, ValueError):
            errors["due_date"] = "Due date must use YYYY-MM-DD format."
    return errors


@app.get("/")
def home():
    return send_from_directory(".", "index.html")


@app.get("/api/health")
def health_check():
    return jsonify({"status": "ok"})


@app.get("/api/tasks")
def list_tasks():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "all")
    priority = request.args.get("priority", "all")
    query = "SELECT * FROM tasks WHERE 1 = 1"
    parameters = []
    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        parameters.extend([f"%{search}%", f"%{search}%"])
    if status in VALID_STATUSES:
        query += " AND status = ?"
        parameters.append(status)
    if priority in VALID_PRIORITIES:
        query += " AND priority = ?"
        parameters.append(priority)
    query += " ORDER BY CASE status WHEN 'in_progress' THEN 1 WHEN 'todo' THEN 2 ELSE 3 END, id DESC"
    with get_connection() as connection:
        tasks = connection.execute(query, parameters).fetchall()
    return jsonify([serialize_task(task) for task in tasks])


@app.get("/api/stats")
def task_stats():
    with get_connection() as connection:
        totals = connection.execute(
            "SELECT COUNT(*) AS total, SUM(status = 'done') AS done, SUM(status = 'in_progress') AS active FROM tasks"
        ).fetchone()
    total = totals["total"] or 0
    return jsonify({
        "total": total,
        "done": totals["done"] or 0,
        "active": totals["active"] or 0,
        "remaining": total - (totals["done"] or 0),
    })


@app.post("/api/tasks")
def create_task():
    payload = request.get_json(silent=True) or {}
    errors = validate_task_payload(payload)
    if errors:
        return jsonify({"errors": errors}), 400
    task_data = (
        payload["title"].strip(),
        (payload.get("description") or "").strip(),
        payload.get("status", "todo"),
        payload.get("priority", "medium"),
        payload.get("due_date") or None,
        datetime.utcnow().isoformat(timespec="seconds"),
    )
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, description, status, priority, due_date, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            task_data,
        )
        task = connection.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(serialize_task(task)), 201


@app.patch("/api/tasks/<int:task_id>")
def update_task(task_id):
    payload = request.get_json(silent=True) or {}
    errors = validate_task_payload(payload, partial=True)
    if errors:
        return jsonify({"errors": errors}), 400
    allowed_fields = {"title", "description", "status", "priority", "due_date"}
    updates = {field: payload[field] for field in allowed_fields if field in payload}
    if "title" in updates:
        updates["title"] = updates["title"].strip()
    if "description" in updates:
        updates["description"] = (updates["description"] or "").strip()
    if "due_date" in updates and not updates["due_date"]:
        updates["due_date"] = None
    if not updates:
        return jsonify({"error": "No changes provided."}), 400
    assignments = ", ".join(f"{field} = ?" for field in updates)
    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE tasks SET {assignments} WHERE id = ?",
            [*updates.values(), task_id],
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "Task not found."}), 404
        task = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(serialize_task(task))


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    if cursor.rowcount == 0:
        return jsonify({"error": "Task not found."}), 404
    return ("", 204)


initialize_database()

if __name__ == "__main__":
    app.run(debug=True)
