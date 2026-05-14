import datetime
import re
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import (
    get_db,
    init_db,
    seed_db,
    create_user,
    get_user_by_email,
    add_expense as db_add_expense,
)
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
    get_expense_by_id,
    update_expense,
)

app = Flask(__name__)
app.secret_key = "dev-secret-change-in-prod"  # replace in production

VALID_CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name:
        return render_template("register.html", error="Name is required.")
    if not email:
        return render_template("register.html", error="Email is required.")
    if len(password) < 8:
        return render_template(
            "register.html", error="Password must be at least 8 characters."
        )

    try:
        create_user(name, email, generate_password_hash(password))
    except sqlite3.IntegrityError:
        return render_template(
            "register.html", error="An account with that email already exists."
        )

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Email and password are required.")

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    uid = session["user_id"]
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    user = get_user_by_id(uid)
    summary = get_summary_stats(uid, date_from, date_to)
    transactions = get_recent_transactions(uid, date_from, date_to)
    categories = get_category_breakdown(uid, date_from, date_to)

    return render_template(
        "profile.html",
        user=user,
        summary=summary,
        transactions=transactions,
        categories=categories,
        date_from=date_from,
        date_to=date_to,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template("add_expense.html")

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    def re_render(error):
        return render_template(
            "add_expense.html",
            error=error,
            amount=amount_raw,
            category=category,
            date=date,
            description=description,
        )

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return re_render("Amount must be a positive number.")

    if category not in VALID_CATEGORIES:
        return re_render("Please select a valid category.")

    if not date:
        return re_render("Date is required.")

    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        return re_render("Please enter a valid date (YYYY-MM-DD).")

    db_add_expense(session["user_id"], amount, category, date, description or None)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id)
    if expense is None:
        abort(404)
    if expense["user_id"] != session["user_id"]:
        abort(403)

    if request.method == "GET":
        return render_template(
            "edit_expense.html", expense=expense, categories=VALID_CATEGORIES
        )

    amount_str = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    candidate = {
        **expense,
        "amount": amount_str,
        "category": category,
        "date": date,
        "description": description,
    }

    def rerender(error):
        return render_template(
            "edit_expense.html",
            expense=candidate,
            categories=VALID_CATEGORIES,
            error=error,
        )

    try:
        amount = float(amount_str)
    except ValueError:
        return rerender("Amount must be a number.")
    if amount <= 0:
        return rerender("Amount must be greater than zero.")
    if not _DATE_RE.match(date):
        return rerender("Date must be in YYYY-MM-DD format.")
    if category not in VALID_CATEGORIES:
        return rerender("Please select a valid category.")

    update_expense(id, amount, category, date, description)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
