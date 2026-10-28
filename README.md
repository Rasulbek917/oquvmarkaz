# Oʻquv markazi — boshqaruv tizimi (Flask)

Oʻquv markazi uchun kichik boshqaruv tizimi: guruhlar, oʻquvchilar, davomat,
uy vazifalari, baholar va toʻlovlar. Flask + SQLite asosida yozilgan, bitta
`sayt.py` faylida.

## Demo loginlar

| Rol       | Login        | Parol        |
|-----------|--------------|--------------|
| Oʻqituvchi | `oqituvchi`  | `teacher123` |
| Oʻquvchi   | `student1`   | `student123` |

> Birinchi ishga tushirishda boʻsh baza avtomatik yaratiladi va demo
> maʼlumotlar bilan toʻldiriladi. Oʻquvchi qoʻshilganda uning login/paroli
> `student<id>` / `student123` boʻladi.

## Lokal ishga tushirish

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python sayt.py
# http://127.0.0.1:5000
```

Maʼlumotlar `oquv.db` faylida saqlanadi. Boshqa faylni ishlatish uchun:

```bash
DB_PATH=/tmp/mening-bazam.db python sayt.py
```

## Vercel'ga deploy qilish

Loyiha Vercel'ning zero-config Python runtime'i uchun tayyorlangan.

Muhim fayllar:

| Fayl               | Vazifasi                                                        |
|--------------------|-----------------------------------------------------------------|
| `pyproject.toml`   | `[tool.vercel] entrypoint = "sayt:app"` — Flask ilovasi qayerdaligi |
| `requirements.txt` | Python bogʻliqliklari (Flask, Werkzeug)                          |
| `.python-version`  | Python 3.12                                                      |
| `.vercelignore`    | `.venv`, `__pycache__`, `*.db` kabi fayllar bundle'ga kirmaydi    |

`sayt.py` fayli nomi Vercel'ning standart entrypoint nomlari
(`app.py`, `index.py`, `main.py`, `server.py`, `wsgi.py`, `asgi.py`) roʻyxatiga
kirmagani uchun `pyproject.toml` ichida entrypoint aniq koʻrsatilgan.

### CLI orqali

```bash
npm i -g vercel
vercel login
vercel          # preview
vercel --prod   # production
```

### GitHub orqali

1. GitHub'da repo'ni Vercel'ga ulang (Add New → Project).
2. Framework Preset: **Other** (avtomatik aniqlanadi).
3. Root Directory: repo ildizi.
4. Deploy.

### Environment variables (Vercel → Settings → Environment Variables)

| Nomi         | Qiymat                                                        |
|--------------|---------------------------------------------------------------|
| `SECRET_KEY` | Uzun, tasodifiy, maxfiy satr (production uchun majburiy)       |
| `DB_PATH`    | Ixtiyoriy. Boʻsh qoldirilsa Vercel'da `/tmp/oquv.db` ishlatiladi |

### Muhim eslatma: SQLite va Vercel

Vercel Functions fayl tizimi faqat `/tmp` ichida yozishga ruxsat beradi va u
**doimiy emas**. Shu sababli:

- Har bir yangi instance (cold start) yoki yangi deploy'da baza qaytadan
  yaratiladi va demo maʼlumotlar bilan toʻladi.
- Kiritilgan real maʼlumotlar saqlanib qolmaydi.

Doimiy maʼlumot kerak boʻlsa, SQLite oʻrniga tashqi bazaga oʻtish kerak:
Turso (libSQL), Neon/Supabase (Postgres) yoki Vercel Postgres.

## Loyiha tuzilishi

```
sayt.py           # butun ilova: routes, SQLite sxemasi, HTML shablon
pyproject.toml    # Vercel entrypoint
requirements.txt  # bogʻliqliklar
.python-version   # Python versiyasi
.vercelignore     # deploy'ga kirmaydigan fayllar
```

## Marshrutlar

| Yoʻl                | Kim uchun   | Vazifasi                    |
|---------------------|-------------|-----------------------------|
| `/login`, `/logout` | hamma       | Kirish / chiqish            |
| `/`                 | hamma       | Bosh sahifa, statistika     |
| `/groups`           | oʻqituvchi  | Guruhlar CRUD               |
| `/students`         | oʻqituvchi  | Oʻquvchilar, qidiruv, filtr |
| `/attendance`       | oʻqituvchi  | Kunlik davomat              |
| `/homework`         | hamma       | Vazifalar va baholar        |
| `/score`            | oʻqituvchi  | Baho qoʻyish                |
| `/payments`         | hamma       | Toʻlov holati               |
| `/delete/...`       | oʻqituvchi  | Yozuvni oʻchirish           |
