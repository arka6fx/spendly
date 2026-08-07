def _date_clause(date_from, date_to):
    clause = ""
    params = []
    if date_from:
        clause += " AND date >= ?"
        params.append(date_from)
    if date_to:
        clause += " AND date <= ?"
        params.append(date_to)
    return clause, params


async def get_user_by_email(db, email):
    return await db.prepare("SELECT * FROM users WHERE email = ?").bind(email).first()


async def get_user_by_id(db, user_id):
    return await (
        db.prepare("SELECT name, email, created_at FROM users WHERE id = ?")
        .bind(user_id)
        .first()
    )


async def create_user(db, name, email, password_hash):
    await (
        db.prepare(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)"
        )
        .bind(name, email, password_hash)
        .run()
    )


async def add_expense(db, user_id, amount, category, expense_date, description):
    await (
        db.prepare(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)"
        )
        .bind(user_id, amount, category, expense_date, description)
        .run()
    )


async def delete_expense(db, expense_id):
    await db.prepare("DELETE FROM expenses WHERE id = ?").bind(expense_id).run()


async def update_expense(db, expense_id, amount, category, date, description):
    await (
        db.prepare(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ?"
            " WHERE id = ?"
        )
        .bind(amount, category, date, description, expense_id)
        .run()
    )


async def get_expense_by_id(db, expense_id):
    return await (
        db.prepare(
            "SELECT id, user_id, amount, category, date, description"
            " FROM expenses WHERE id = ?"
        )
        .bind(expense_id)
        .first()
    )


async def get_summary_stats(db, user_id, date_from=None, date_to=None):
    clause, params = _date_clause(date_from, date_to)
    row = await (
        db.prepare(
            "SELECT COALESCE(SUM(amount), 0.0) AS total_spent, COUNT(*) AS total_count"
            " FROM expenses WHERE user_id = ?" + clause
        )
        .bind(user_id, *params)
        .first()
    )
    top = await (
        db.prepare(
            "SELECT category FROM expenses WHERE user_id = ?" + clause
            + " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1"
        )
        .bind(user_id, *params)
        .first()
    )
    return {
        "total_spent": float(row["total_spent"] or 0),
        "total_count": int(row["total_count"]),
        "top_category": top["category"] if top else None,
    }


async def get_recent_transactions(db, user_id, date_from=None, date_to=None, limit=None):
    clause, params = _date_clause(date_from, date_to)
    sql = (
        "SELECT id, date, description, category, amount FROM expenses"
        " WHERE user_id = ?" + clause + " ORDER BY date DESC"
    )
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    result = await db.prepare(sql).bind(user_id, *params).all()
    return result.results


async def get_category_breakdown(db, user_id, date_from=None, date_to=None):
    clause, params = _date_clause(date_from, date_to)
    result = await (
        db.prepare(
            "SELECT category AS name, SUM(amount) AS total FROM expenses"
            " WHERE user_id = ?" + clause + " GROUP BY category ORDER BY total DESC"
        )
        .bind(user_id, *params)
        .all()
    )
    return result.results
