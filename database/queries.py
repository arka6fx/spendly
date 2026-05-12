from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        formatted = datetime.strptime(row["created_at"][:10], "%Y-%m-%d").strftime("%B %Y")
        return {"name": row["name"], "email": row["email"], "created_at": formatted}
    finally:
        conn.close()


def get_summary_stats(user_id):
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0.0) AS total_spent, COUNT(*) AS total_count FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        top = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return {
            "total_spent": float(totals["total_spent"]),
            "total_count": int(totals["total_count"]),
            "top_category": top["category"] if top else None,
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_category_breakdown(user_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category AS name, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC",
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
