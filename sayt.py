
import os
import sqlite3
from datetime import date
from functools import wraps

from flask import (
    Flask, flash, g, redirect, render_template_string,
    request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-ozgartiring")

DB = os.environ.get(
    "DB_PATH",
    "/tmp/oquv.db" if os.environ.get("VERCEL") else "oquv.db"
)

STATUS = {
    "F": ("Toʻlandi", "ok"),
    "P": ("Qisman", "wa"),
    "U": ("Toʻlanmadi", "er")
}
NEXT = {"U": "P", "P": "F", "F": "U"}


# ---------- Baza ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d is not None:
        d.close()


def init_db():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")

    con.executescript("""
    CREATE TABLE IF NOT EXISTS groups(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        time TEXT
    );

    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        gid INTEGER REFERENCES groups(id) ON DELETE CASCADE,
        phone TEXT,
        pay INTEGER DEFAULT 300000,
        status TEXT DEFAULT 'U'
    );

    CREATE TABLE IF NOT EXISTS attendance(
        day TEXT,
        sid INTEGER REFERENCES students(id) ON DELETE CASCADE,
        present INTEGER,
        PRIMARY KEY(day, sid)
    );

    CREATE TABLE IF NOT EXISTS homework(
        id INTEGER PRIMARY KEY,
        gid INTEGER REFERENCES groups(id) ON DELETE CASCADE,
        title TEXT,
        due TEXT
    );

    CREATE TABLE IF NOT EXISTS scores(
        hid INTEGER REFERENCES homework(id) ON DELETE CASCADE,
        sid INTEGER REFERENCES students(id) ON DELETE CASCADE,
        score INTEGER,
        PRIMARY KEY(hid, sid)
    );

    CREATE TABLE IF NOT EXISTS users(
        login TEXT PRIMARY KEY,
        pw TEXT,
        role TEXT,
        sid INTEGER
    );
    """)

    # Demo ma'lumotlar faqat bo'sh bazada yaratiladi.
    if not con.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        con.execute(
            "INSERT INTO users VALUES(?,?,?,NULL)",
            (
                "oqituvchi",
                generate_password_hash("teacher123"),
                "T"
            )
        )

        con.executemany(
            "INSERT INTO groups(name,time) VALUES(?,?)",
            [
                ("Beginner A1", "Du/Chor/Juma 09:00"),
                ("IELTS 6.5", "Sesh/Pay/Shan 15:00")
            ]
        )

        demo_students = [
            ("Aziza Karimova", 1, "+998 90 123 45 67", 300000, "P"),
            ("Jasur Toshmatov", 1, "+998 91 234 56 78", 300000, "U"),
            ("Madina Ergasheva", 2, "+998 93 345 67 89", 450000, "F")
        ]

        for name, gid, phone, pay, status in demo_students:
            cur = con.execute(
                """
                INSERT INTO students(name,gid,phone,pay,status)
                VALUES(?,?,?,?,?)
                """,
                (name, gid, phone, pay, status)
            )

            con.execute(
                "INSERT INTO users VALUES(?,?,?,?)",
                (
                    f"student{cur.lastrowid}",
                    generate_password_hash("student123"),
                    "S",
                    cur.lastrowid
                )
            )

        con.execute(
            """
            INSERT INTO homework(gid,title,due)
            VALUES(1, 'Unit 3: Present Simple', ?)
            """,
            (str(date.today()),)
        )

    con.commit()
    con.close()


# Vercel ilovani import qilganda ham bazani tayyorlaydi.
# IF NOT EXISTS mavjud jadvallarni qayta yaratmaydi.
init_db()


# ---------- Yordamchilar ----------
def money(n):
    return f"{int(n or 0):,}".replace(",", " ") + " soʻm"


def fdate(s):
    return ".".join(reversed(s.split("-"))) if s else "—"


app.jinja_env.filters.update(money=money, fdate=fdate)


def login_required(role=None):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            if "role" not in session:
                return redirect(url_for("login"))

            if role and session["role"] != role:
                flash("Ruxsat yoʻq")
                return redirect(url_for("home"))

            return f(*a, **k)
        return w
    return deco


def attendance_pct(sid):
    r = db().execute(
        """
        SELECT COUNT(*) AS c, SUM(present) AS p
        FROM attendance
        WHERE sid=?
        """,
        (sid,)
    ).fetchone()

    return round(100 * r["p"] / r["c"]) if r["c"] else None


# ---------- Shablon ----------
BASE = """<!doctype html><html lang="uz"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Oʻquv markazi</title>
<style>
:root{--bg:#f6f7fb;--card:#fff;--tx:#161a2b;--mu:#6b7186;--bd:#e6e8f0;--ac:#4f46e5;--ok:#16a34a;--wa:#d97706;--er:#dc2626}
@media(prefers-color-scheme:dark){:root{--bg:#0f1220;--card:#181c2f;--tx:#eef0fa;--mu:#9aa1bb;--bd:#2a2f47;--ac:#818cf8;--ok:#4ade80;--wa:#fbbf24;--er:#f87171}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.45 system-ui,sans-serif}
header{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center;padding:12px 16px;border-bottom:1px solid var(--bd)}
header b{margin-right:auto}a{color:var(--ac);text-decoration:none}nav a{margin-right:12px}
main{max-width:760px;margin:0 auto;padding:16px}.card{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:14px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.stat b{display:block;font-size:24px}.mu{color:var(--mu);font-size:13px}
button,input,select{font:inherit;color:var(--tx);background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:9px 11px}
input,select{width:100%}form.f{display:grid;gap:8px}.pri{background:var(--ac);color:#fff;border-color:var(--ac);cursor:pointer}
.row{display:flex;gap:8px;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--bd)}.row:last-child{border:0}
.badge{font-size:12px;padding:3px 9px;border-radius:99px;border:1px solid currentColor;background:none;cursor:pointer}
.ok{color:var(--ok)}.wa{color:var(--wa)}.er{color:var(--er)}.msg{background:var(--ac);color:#fff;padding:9px 14px;border-radius:10px;margin-bottom:12px}
.sm{padding:5px 10px;font-size:13px;cursor:pointer}form.i{display:inline}
</style></head><body>
{% if session.role %}<header><b>📚 Oʻquv markazi</b><nav>
<a href="{{ url_for('home') }}">Bosh</a>
{% if session.role=='T' %}<a href="{{ url_for('groups') }}">Guruh</a><a href="{{ url_for('students') }}">Oʻquvchi</a>
<a href="{{ url_for('attendance') }}">Davomat</a>{% endif %}
<a href="{{ url_for('homework') }}">Vazifa</a><a href="{{ url_for('payments') }}">Toʻlov</a></nav>
<a href="{{ url_for('logout') }}">Chiqish</a></header>{% endif %}
<main>{% for m in get_flashed_messages() %}<div class="msg">{{ m }}</div>{% endfor %}
{% if page=='login' %}
<div class="card"><h2>Kirish</h2><form class="f" method="post"><input name="login" placeholder="Login" required>
<input name="password" type="password" placeholder="Parol" required><button class="pri">Kirish</button></form>
<p class="mu">Demo: oqituvchi / teacher123 · student1 / student123</p></div>
{% elif page=='home' %}
{% if session.role=='T' %}<div class="grid">
<div class="card stat"><b>{{ d.students }}</b><span class="mu">Oʻquvchilar</span></div>
<div class="card stat"><b>{{ d.groups }}</b><span class="mu">Guruhlar</span></div>
<div class="card stat"><b>{{ d.hw }}</b><span class="mu">Uy vazifalari</span></div>
<div class="card stat"><b class="er" style="font-size:17px">{{ d.debt|money }}</b><span class="mu">Qarzdorlik</span></div></div>
<div class="card"><b class="ok">{{ d.paid|money }}</b><br><span class="mu">Shu oy tushgan</span></div>
{% else %}<div class="card"><h2>{{ d.s.name if d.s else 'Oʻquvchi topilmadi' }}</h2>
{% if d.s %}<span class="mu">{{ d.s.gname }} · {{ d.s.time or '—' }}</span>{% endif %}</div>
<div class="grid"><div class="card stat"><b>{{ d.att if d.att is not none else '—' }}{{ '%' if d.att is not none }}</b><span class="mu">Davomat</span></div>
<div class="card stat"><b>{{ d.avg if d.avg is not none else '—' }}</b><span class="mu">Oʻrtacha baho</span></div></div>{% endif %}
{% elif page=='groups' %}
<div class="card"><form class="f" method="post" action="{{ url_for('groups') }}"><input name="name" placeholder="Guruh nomi" required>
<input name="time" placeholder="Dars vaqti"><button class="pri">+ Guruh qoʻshish</button></form></div>
<div class="card">{% for r in rows %}<div class="row"><div><b>{{ r.name }}</b><br><span class="mu">{{ r.time }} · {{ r.n }} oʻquvchi</span></div>
<form class="i" method="post" action="{{ url_for('delete', table='groups', id=r.id) }}" onsubmit="return confirm('Oʻchirilsinmi?')">
<button class="sm er">Oʻchirish</button></form></div>{% else %}<p class="mu">Guruhlar yoʻq</p>{% endfor %}</div>
{% elif page=='students' %}
<div class="card"><form class="f" method="post"><input name="name" placeholder="Ism familiya" required><input name="phone" placeholder="Telefon">
<select name="gid" required {% if not groups %}disabled{% endif %}>
{% for x in groups %}<option value="{{ x.id }}">{{ x.name }}</option>{% endfor %}
</select>
<input name="pay" type="number" min="0" placeholder="Oylik toʻlov (soʻm)">
<button class="pri" {% if not groups %}disabled{% endif %}>+ Oʻquvchi qoʻshish</button>
{% if not groups %}<span class="mu">Avval guruh yarating.</span>{% endif %}
</form></div>
<form class="grid" method="get" style="margin-bottom:12px"><input name="q" value="{{ q }}" placeholder="🔎 Qidirish">
<select name="gid" onchange="this.form.submit()"><option value="">Barcha guruhlar</option>
{% for x in groups %}<option value="{{ x.id }}" {{ 'selected' if gid==x.id|string }}>{{ x.name }}</option>{% endfor %}</select></form>
<div class="card">{% for r in rows %}<div class="row"><div><b>{{ r.name }}</b><br><span class="mu">{{ r.gname }} · {{ r.phone }} · login: student{{ r.id }}</span></div>
<form class="i" method="post" action="{{ url_for('delete', table='students', id=r.id) }}" onsubmit="return confirm('Oʻchirilsinmi?')">
<button class="sm er">✕</button></form></div>{% else %}<p class="mu">Oʻquvchi topilmadi</p>{% endfor %}</div>
{% elif page=='attendance' %}
<form class="grid" method="get" style="margin-bottom:12px"><select name="gid" onchange="this.form.submit()">
{% for x in groups %}<option value="{{ x.id }}" {{ 'selected' if gid==x.id }}>{{ x.name }}</option>{% endfor %}</select>
<input type="date" name="day" value="{{ day }}" onchange="this.form.submit()"></form>
<div class="card"><h3>{{ day|fdate }}</h3>{% for r in rows %}<div class="row"><b>{{ r.name }}</b>
<form class="i" method="post"><input type="hidden" name="sid" value="{{ r.id }}"><input type="hidden" name="day" value="{{ day }}">
<input type="hidden" name="gid" value="{{ gid }}">
<button class="sm {{ 'pri' if r.present==1 }}" name="present" value="1" style="width:auto">Keldi</button>
<button class="sm {{ 'er' if r.present==0 }}" name="present" value="0" style="width:auto">Kelmadi</button></form></div>
{% else %}<p class="mu">Bu guruhda oʻquvchi yoʻq</p>{% endfor %}</div>
{% elif page=='homework' %}
{% if session.role=='T' %}<div class="card"><form class="f" method="post"><input name="title" placeholder="Vazifa nomi" required>
<select name="gid" required {% if not groups %}disabled{% endif %}>{% for x in groups %}<option value="{{ x.id }}">{{ x.name }}</option>{% endfor %}</select>
<input type="date" name="due" value="{{ today }}"><button class="pri" {% if not groups %}disabled{% endif %}>+ Vazifa qoʻshish</button>
{% if not groups %}<span class="mu">Avval guruh yarating.</span>{% endif %}
</form></div>
{% for h in rows %}<div class="card"><div class="row" style="border:0"><div><b>{{ h.title }}</b><br><span class="mu">{{ h.gname }} · {{ h.due|fdate }}</span></div>
<form class="i" method="post" action="{{ url_for('delete', table='homework', id=h.id) }}"><button class="sm er">✕</button></form></div>
{% for s in h.students %}<form class="row" method="post" action="{{ url_for('score') }}"><span>{{ s.name }}</span>
<input type="hidden" name="hid" value="{{ h.id }}"><input type="hidden" name="sid" value="{{ s.id }}">
<input name="score" type="number" min="0" max="100" value="{{ s.score if s.score is not none }}" placeholder="0–100" style="width:90px" onchange="this.form.submit()"></form>{% endfor %}</div>{% endfor %}
{% else %}<div class="card">{% for h in rows %}<div class="row"><div><b>{{ h.title }}</b><br><span class="mu">Muddat: {{ h.due|fdate }}</span></div>
<span class="badge {{ 'ok' if h.score is not none else 'wa' }}">{{ (h.score|string + '/100') if h.score is not none else 'Kutilmoqda' }}</span></div>
{% else %}<p class="mu">Vazifalar yoʻq</p>{% endfor %}</div>{% endif %}
{% elif page=='payments' %}
<div class="card">{% for s in rows %}<div class="row"><div><b>{{ s.name }}</b><br><span class="mu">{{ s.pay|money }}</span></div>
{% if session.role=='T' %}<form class="i" method="post" action="{{ url_for('pay_status', id=s.id) }}">
<button class="badge {{ st[s.status][1] }}">{{ st[s.status][0] }}</button></form>
{% else %}<span class="badge {{ st[s.status][1] }}">{{ st[s.status][0] }}</span>{% endif %}</div>
{% else %}<p class="mu">Oʻquvchilar yoʻq</p>{% endfor %}</div>
{% endif %}</main></body></html>"""


def render(page, **kw):
    return render_template_string(
        BASE,
        page=page,
        st=STATUS,
        today=str(date.today()),
        **kw
    )


# ---------- Yoʻllar ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_name = request.form.get("login", "").strip().lower()
        password = request.form.get("password", "")

        u = db().execute(
            "SELECT * FROM users WHERE login=?",
            (login_name,)
        ).fetchone()

        if u and check_password_hash(u["pw"], password):
            session.clear()
            session.update(role=u["role"], sid=u["sid"])
            return redirect(url_for("home"))

        flash("Login yoki parol notoʻgʻri")

    return render("login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required()
def home():
    c = db()

    if session["role"] == "T":
        def one(q):
            return c.execute(q).fetchone()[0] or 0

        d = dict(
            students=one("SELECT COUNT(*) FROM students"),
            groups=one("SELECT COUNT(*) FROM groups"),
            hw=one("SELECT COUNT(*) FROM homework"),
            debt=one("SELECT SUM(pay) FROM students WHERE status!='F'"),
            paid=one("SELECT SUM(pay) FROM students WHERE status='F'")
        )
    else:
        s = c.execute(
            """
            SELECT s.*, g.name AS gname, g.time
            FROM students s
            LEFT JOIN groups g ON g.id=s.gid
            WHERE s.id=?
            """,
            (session["sid"],)
        ).fetchone()

        a = c.execute(
            "SELECT AVG(score) FROM scores WHERE sid=?",
            (session["sid"],)
        ).fetchone()[0]

        d = dict(
            s=s,
            att=attendance_pct(session["sid"]),
            avg=round(a) if a is not None else None
        )

    return render("home", d=d)


@app.route("/groups", methods=["GET", "POST"])
@login_required("T")
def groups():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        time = request.form.get("time", "").strip() or "—"

        if not name:
            flash("Guruh nomini kiriting.")
            return redirect(url_for("groups"))

        db().execute(
            "INSERT INTO groups(name,time) VALUES(?,?)",
            (name, time)
        )
        db().commit()
        flash("Guruh qoʻshildi")
        return redirect(url_for("groups"))

    rows = db().execute(
        """
        SELECT g.*,
               (SELECT COUNT(*) FROM students WHERE gid=g.id) AS n
        FROM groups g
        ORDER BY g.id
        """
    ).fetchall()

    return render("groups", rows=rows)


@app.route("/students", methods=["GET", "POST"])
@login_required("T")
def students():
    c = db()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip() or "—"
        gid = request.form.get("gid", type=int)

        try:
            pay = int(request.form.get("pay") or 300000)
            if pay < 0:
                raise ValueError
        except (TypeError, ValueError):
            flash("Oylik toʻlovni toʻgʻri kiriting.")
            return redirect(url_for("students"))

        group = c.execute(
            "SELECT id FROM groups WHERE id=?",
            (gid,)
        ).fetchone()

        if not name:
            flash("Oʻquvchi ismini kiriting.")
            return redirect(url_for("students"))

        if not group:
            flash("Avval guruh yarating yoki mavjud guruhni tanlang.")
            return redirect(url_for("students"))

        cur = c.execute(
            """
            INSERT INTO students(name,gid,phone,pay)
            VALUES(?,?,?,?)
            """,
            (name, gid, phone, pay)
        )

        c.execute(
            "INSERT INTO users VALUES(?,?,?,?)",
            (
                f"student{cur.lastrowid}",
                generate_password_hash("student123"),
                "S",
                cur.lastrowid
            )
        )

        c.commit()
        flash("Oʻquvchi qoʻshildi (parol: student123)")
        return redirect(url_for("students"))

    q = request.args.get("q", "").strip()
    gid = request.args.get("gid", "")

    sql = """
        SELECT s.*, g.name AS gname
        FROM students s
        LEFT JOIN groups g ON g.id=s.gid
        WHERE s.name LIKE ?
    """
    args = [f"%{q}%"]

    if gid:
        sql += " AND s.gid=?"
        args.append(gid)

    rows = c.execute(sql, args).fetchall()
    groups_list = c.execute(
        "SELECT * FROM groups ORDER BY id"
    ).fetchall()

    return render(
        "students",
        rows=rows,
        groups=groups_list,
        q=q,
        gid=gid
    )


@app.route("/attendance", methods=["GET", "POST"])
@login_required("T")
def attendance():
    c = db()

    if request.method == "POST":
        f = request.form
        sid = f.get("sid", type=int)
        gid = f.get("gid", type=int)
        day = f.get("day", "")
        present = f.get("present", type=int)

        if present not in (0, 1) or not day:
            flash("Davomat maʼlumotlari notoʻgʻri.")
            return redirect(url_for("attendance"))

        student = c.execute(
            "SELECT id FROM students WHERE id=? AND gid=?",
            (sid, gid)
        ).fetchone()

        if not student:
            flash("Oʻquvchi topilmadi.")
            return redirect(url_for("attendance"))

        c.execute(
            """
            INSERT INTO attendance(day,sid,present)
            VALUES(?,?,?)
            ON CONFLICT(day,sid)
            DO UPDATE SET present=excluded.present
            """,
            (day, sid, present)
        )
        c.commit()

        return redirect(
            url_for("attendance", gid=gid, day=day)
        )

    gs = c.execute(
        "SELECT * FROM groups ORDER BY id"
    ).fetchall()

    gid = request.args.get("gid", type=int)
    if not gid and gs:
        gid = gs[0]["id"]

    day = request.args.get("day") or str(date.today())

    rows = []
    if gid:
        rows = c.execute(
            """
            SELECT s.id, s.name, a.present
            FROM students s
            LEFT JOIN attendance a
              ON a.sid=s.id AND a.day=?
            WHERE s.gid=?
            ORDER BY s.name
            """,
            (day, gid)
        ).fetchall()

    return render(
        "attendance",
        groups=gs,
        gid=gid or 0,
        day=day,
        rows=rows
    )


@app.route("/homework", methods=["GET", "POST"])
@login_required()
def homework():
    c = db()

    if request.method == "POST" and session["role"] == "T":
        title = request.form.get("title", "").strip()
        gid = request.form.get("gid", type=int)
        due = request.form.get("due") or str(date.today())

        group = c.execute(
            "SELECT id FROM groups WHERE id=?",
            (gid,)
        ).fetchone()

        if not title:
            flash("Vazifa nomini kiriting.")
            return redirect(url_for("homework"))

        if not group:
            flash("Avval guruh yarating yoki mavjud guruhni tanlang.")
            return redirect(url_for("homework"))

        c.execute(
            "INSERT INTO homework(gid,title,due) VALUES(?,?,?)",
            (gid, title, due)
        )
        c.commit()
        flash("Vazifa qoʻshildi")
        return redirect(url_for("homework"))

    if session["role"] == "T":
        rows = [
            dict(h) for h in c.execute(
                """
                SELECT h.*, g.name AS gname
                FROM homework h
                LEFT JOIN groups g ON g.id=h.gid
                ORDER BY h.id DESC
                """
            ).fetchall()
        ]

        for h in rows:
            h["students"] = c.execute(
                """
                SELECT s.id, s.name, sc.score
                FROM students s
                LEFT JOIN scores sc
                  ON sc.sid=s.id AND sc.hid=?
                WHERE s.gid=?
                ORDER BY s.name
                """,
                (h["id"], h["gid"])
            ).fetchall()

        return render(
            "homework",
            rows=rows,
            groups=c.execute(
                "SELECT * FROM groups ORDER BY id"
            ).fetchall()
        )

    rows = c.execute(
        """
        SELECT h.*, sc.score
        FROM homework h
        JOIN students s ON s.gid=h.gid AND s.id=?
        LEFT JOIN scores sc ON sc.hid=h.id AND sc.sid=s.id
        ORDER BY h.id DESC
        """,
        (session["sid"],)
    ).fetchall()

    return render("homework", rows=rows)


@app.post("/score")
@login_required("T")
def score():
    f = request.form
    hid = f.get("hid", type=int)
    sid = f.get("sid", type=int)
    raw_score = f.get("score", "").strip()

    c = db()

    valid = c.execute(
        """
        SELECT 1
        FROM homework h
        JOIN students s ON s.gid=h.gid
        WHERE h.id=? AND s.id=?
        """,
        (hid, sid)
    ).fetchone()

    if not valid:
        flash("Vazifa yoki oʻquvchi topilmadi.")
        return redirect(url_for("homework"))

    if raw_score == "":
        c.execute(
            "DELETE FROM scores WHERE hid=? AND sid=?",
            (hid, sid)
        )
    else:
        try:
            v = int(raw_score)
            if not 0 <= v <= 100:
                raise ValueError
        except ValueError:
            flash("Baho 0 dan 100 gacha bo‘lishi kerak.")
            return redirect(url_for("homework"))

        c.execute(
            """
            INSERT INTO scores(hid,sid,score)
            VALUES(?,?,?)
            ON CONFLICT(hid,sid)
            DO UPDATE SET score=excluded.score
            """,
            (hid, sid, v)
        )

    c.commit()
    return redirect(url_for("homework"))


@app.route("/payments")
@login_required()
def payments():
    if session["role"] == "T":
        rows = db().execute(
            "SELECT * FROM students ORDER BY name"
        ).fetchall()
    else:
        rows = db().execute(
            "SELECT * FROM students WHERE id=?",
            (session["sid"],)
        ).fetchall()

    return render("payments", rows=rows)


@app.post("/payments/<int:id>")
@login_required("T")
def pay_status(id):
    c = db()

    s = c.execute(
        "SELECT status FROM students WHERE id=?",
        (id,)
    ).fetchone()

    if s and s["status"] in NEXT:
        c.execute(
            "UPDATE students SET status=? WHERE id=?",
            (NEXT[s["status"]], id)
        )
        c.commit()
    else:
        flash("Oʻquvchi topilmadi.")

    return redirect(url_for("payments"))


@app.post("/delete/<table>/<int:id>")
@login_required("T")
def delete(table, id):
    if table not in ("groups", "students", "homework"):
        return redirect(url_for("home"))

    c = db()

    if table == "groups":
        # Guruh o'chirilganda unga tegishli loginlar ham o'chiriladi.
        student_ids = c.execute(
            "SELECT id FROM students WHERE gid=?",
            (id,)
        ).fetchall()

        for student in student_ids:
            c.execute(
                "DELETE FROM users WHERE sid=?",
                (student["id"],)
            )

    elif table == "students":
        c.execute(
            "DELETE FROM users WHERE sid=?",
            (id,)
        )

    cursor = c.execute(
        f"DELETE FROM {table} WHERE id=?",
        (id,)
    )
    c.commit()

    if cursor.rowcount:
        flash("Oʻchirildi")
    else:
        flash("Oʻchiriladigan maʼlumot topilmadi.")

    return redirect(request.referrer or url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
