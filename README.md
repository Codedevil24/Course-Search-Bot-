# Code Devil Course Bot v3

## Features
- Web service + background polling architecture
- Forced Telegram join gate before bot usage
- Better `/start` welcome UI
- `/search` command
- Normal text search
- Categories
- Exact category filtering
- Featured courses
- Typo suggestions
- Inline search lock for unsubscribed users
- Paid course selling flow
- Premium access grant
- CSV import
- Telegram photo thumbnail save
- Active users analytics
- Render web service compatible

## Structure
- `app.py` -> FastAPI health server
- `bot.py` -> Telegram bot startup and polling
- `config.py` -> environment config
- `db.py` -> Postgres/Supabase queries
- `handlers.py` -> commands, buttons, access guard
- `keyboards.py` -> inline keyboards
- `services.py` -> search service
- `utils.py` -> formatting and force-sub helpers
- `csv_importer.py` -> CSV import helper

## Install
```bash
pip install -r requirements.txt
```

## Run
```bash
uvicorn app:app --host 0.0.0.0 --port 10000
```

## Important
- Bot ko required Telegram channels me add karo.
- Best hai bot ko admin banao, tab membership check reliable rahega.
