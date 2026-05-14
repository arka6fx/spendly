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
        formatted = datetime.strptime(row["created_at"][:10], "%Y-%m-%d").strftime(
            "%B %Y"
        )
        return {"name": row["name"], "email": row["email"], "created_at": formatted}
    finally:
        conn.close()


def _date_clause(user_id, date_from, date_to):
    # Clause is built from hardcoded string fragments only — all values stay in params.
    clause, params = "WHERE user_id = ?", [user_id]
    if date_from:
        clause += " AND date >= ?"
        params.append(date_from)
    if date_to:
        clause += " AND date <= ?"
        params.append(date_to)
    return clause, params


def get_summary_stats(user_id, date_from=None, date_to=None):
    clause, params = _date_clause(user_id, date_from, date_to)
    conn = get_db()
    try:
        totals = conn.execute(
            f"SELECT COALESCE(SUM(amount), 0.0) AS total_spent, COUNT(*) AS total_count FROM expenses {clause}",
            params,
        ).fetchone()
        top = conn.execute(
            f"SELECT category FROM expenses {clause} GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            params,
        ).fetchone()
        return {
            "total_spent": float(totals["total_spent"]),
            "total_count": int(totals["total_count"]),
            "top_category": top["category"] if top else None,
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, date_from=None, date_to=None, limit=None):
    clause, params = _date_clause(user_id, date_from, date_to)
    sql = f"SELECT id, date, description, category, amount FROM expenses {clause} ORDER BY date DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    conn = get_db()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_category_breakdown(user_id, date_from=None, date_to=None):
    clause, params = _date_clause(user_id, date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            f"SELECT category AS name, SUM(amount) AS total FROM expenses {clause} GROUP BY category ORDER BY total DESC",
            params,
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_expense_by_id(expense_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, user_id, amount, category, date, description FROM expenses WHERE id = ?",
            (expense_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_expense(expense_id, amount, category, date, description):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ?",
            (amount, category, date, description, expense_id),
        )
        conn.commit()
    finally:
        conn.close()
