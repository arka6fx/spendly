import datetime
import re
import urllib.parse
from pathlib import Path

import jinja2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

import auth
from database import (
    add_expense as db_add_expense,
    create_user,
    delete_expense as db_delete_expense,
    get_category_breakdown,
    get_expense_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_email,
    get_user_by_id,
    update_expense,
)

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

TEMPLATE_DIR = Path(__file__).parent / "templates"

templates_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=True,
)

app = FastAPI()


async def parse_form(request):
    body = await request.body()
    parsed = urllib.parse.parse_qs(body.decode("utf-8"))
    return {key: values[0] for key, values in parsed.items()}


def get_db(request):
    return request.scope["env"].DB


def current_uid(request):
    secret = request.scope["env"].SESSION_SECRET
    return auth.read_session_token(request.cookies.get(auth.SESSION_COOKIE), secret)


def render(request, name, **context):
    session = {"user_id": current_uid(request)} if current_uid(request) else {}
    html = templates_env.get_template(name).render(session=session, **context)
    return HTMLResponse(html)


def session_response(request, url):
    response = RedirectResponse(url, status_code=303)
    response.delete_cookie(auth.SESSION_COOKIE)
    return response


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #


@app.get("/")
async def landing(request: Request):
    return render(request, "landing.html")


@app.get("/register")
async def register_page(request: Request):
    if current_uid(request):
        return RedirectResponse("/profile")
    return render(request, "register.html")


@app.post("/register")
async def register_post(request: Request):
    if current_uid(request):
        return RedirectResponse("/profile")

    form = await parse_form(request)
    name = form.get("name", "").strip()
    email = form.get("email", "").strip()
    password = form.get("password", "")

    if not name:
        return render(request, "register.html", error="Name is required.")
    if not email:
        return render(request, "register.html", error="Email is required.")
    if len(password) < 8:
        return render(
            request, "register.html", error="Password must be at least 8 characters."
        )

    db = get_db(request)
    if await get_user_by_email(db, email):
        return render(
            request,
            "register.html",
            error="An account with that email already exists.",
        )

    await create_user(db, name, email, auth.hash_password(password))
    return RedirectResponse("/login", status_code=303)


@app.get("/login")
async def login_page(request: Request):
    if current_uid(request):
        return RedirectResponse("/profile")
    return render(request, "login.html")


@app.post("/login")
async def login_post(request: Request):
    if current_uid(request):
        return RedirectResponse("/profile")

    form = await parse_form(request)
    email = form.get("email", "").strip()
    password = form.get("password", "")

    if not email or not password:
        return render(request, "login.html", error="Email and password are required.")

    db = get_db(request)
    user = await get_user_by_email(db, email)
    if user is None or not auth.verify_password(password, user["password_hash"]):
        return render(request, "login.html", error="Invalid email or password.")

    token = auth.make_session_token(user["id"], request.scope["env"].SESSION_SECRET)
    response = RedirectResponse("/profile", status_code=303)
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=auth.SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


@app.get("/logout")
async def logout(request: Request):
    return session_response(request, "/")


@app.get("/terms")
async def terms(request: Request):
    return render(request, "terms.html")


@app.get("/privacy")
async def privacy(request: Request):
    return render(request, "privacy.html")


# ------------------------------------------------------------------ #
# Authed pages                                                        #
# ------------------------------------------------------------------ #


@app.get("/profile")
async def profile(request: Request):
    uid = current_uid(request)
    if not uid:
        return RedirectResponse("/login")

    db = get_db(request)
    date_from = request.query_params.get("date_from", "").strip()
    date_to = request.query_params.get("date_to", "").strip()

    user = await get_user_by_id(db, uid)
    if user is None:
        return RedirectResponse("/login")

    summary = await get_summary_stats(db, uid, date_from, date_to)
    transactions = await get_recent_transactions(db, uid, date_from, date_to)
    categories = await get_category_breakdown(db, uid, date_from, date_to)

    created = user["created_at"] or ""
    if created:
        created = datetime.datetime.strptime(created[:10], "%Y-%m-%d").strftime(
            "%B %Y"
        )
    user_info = {"name": user["name"], "email": user["email"], "created_at": created}

    return render(
        request,
        "profile.html",
        user=user_info,
        summary=summary,
        transactions=transactions,
        categories=categories,
        date_from=date_from,
        date_to=date_to,
    )


@app.get("/expenses/add")
async def add_expense_page(request: Request):
    if not current_uid(request):
        return RedirectResponse("/login")
    return render(request, "add_expense.html")


@app.post("/expenses/add")
async def add_expense_post(request: Request):
    uid = current_uid(request)
    if not uid:
        return RedirectResponse("/login")

    form = await parse_form(request)
    amount_raw = form.get("amount", "").strip()
    category = form.get("category", "").strip()
    date = form.get("date", "").strip()
    description = form.get("description", "").strip()

    def re_render(error):
        return render(
            request,
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

    await db_add_expense(get_db(request), uid, amount, category, date, description or None)
    return RedirectResponse("/profile", status_code=303)


@app.get("/expenses/{expense_id:int}/edit")
async def edit_expense_page(request: Request, expense_id: int):
    uid = current_uid(request)
    if not uid:
        return RedirectResponse("/login")

    db = get_db(request)
    expense = await get_expense_by_id(db, expense_id)
    if expense is None:
        return HTMLResponse("Not Found", status_code=404)
    if expense["user_id"] != uid:
        return HTMLResponse("Forbidden", status_code=403)

    return render(
        request, "edit_expense.html", expense=expense, categories=VALID_CATEGORIES
    )


@app.post("/expenses/{expense_id:int}/edit")
async def edit_expense_post(request: Request, expense_id: int):
    uid = current_uid(request)
    if not uid:
        return RedirectResponse("/login")

    db = get_db(request)
    expense = await get_expense_by_id(db, expense_id)
    if expense is None:
        return HTMLResponse("Not Found", status_code=404)
    if expense["user_id"] != uid:
        return HTMLResponse("Forbidden", status_code=403)

    form = await parse_form(request)
    amount_str = form.get("amount", "").strip()
    category = form.get("category", "").strip()
    date = form.get("date", "").strip()
    description = form.get("description", "").strip()

    candidate = {
        **expense,
        "amount": amount_str,
        "category": category,
        "date": date,
        "description": description,
    }

    def rerender(error):
        return render(
            request,
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

    await update_expense(db, expense_id, amount, category, date, description)
    return RedirectResponse("/profile", status_code=303)


@app.post("/expenses/{expense_id:int}/delete")
async def delete_expense_post(request: Request, expense_id: int):
    uid = current_uid(request)
    if not uid:
        return RedirectResponse("/login")

    db = get_db(request)
    expense = await get_expense_by_id(db, expense_id)
    if expense is None:
        return HTMLResponse("Not Found", status_code=404)
    if expense["user_id"] != uid:
        return HTMLResponse("Forbidden", status_code=403)

    await db_delete_expense(db, expense_id)
    return RedirectResponse("/profile", status_code=303)
