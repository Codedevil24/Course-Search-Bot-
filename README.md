# Code Devil Course Bot v3.1

## New in v3.1
- Non-breaking upgrade over your existing project
- Smart search ranking
- Search/category/featured pagination using `PAGE_SIZE`
- Duplicate course protection
- `/updatecourse`, `/restorecourse`, `/setthumb`, `/pendingpayments`
- Telegram CSV upload import support
- Paid-course access request flow with admin notification
- Safer button error handling
- Better analytics dashboard

## Existing features retained
- Force subscribe gate
- `/start`, `/help`, `/search`
- Normal text search
- Categories
- Featured courses
- Typo suggestions
- Paid/free course flow
- `/addcourse`, `/deletecourse`, `/listcourses`, `/feature`, `/unfeature`, `/stats`, `/grant`, `/importcsv`
- Inline query support
- FastAPI + polling background thread
- Render/UptimeRobot compatible structure

## Run
```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 10000
```

## Important
- `.env` ke existing variable names same rakhe gaye hain.
- Existing callback prefixes `course::`, `cat::`, `suggest::`, `featured::all`, `joincheck::verify` break nahi kiye gaye.
- Old `/addcourse` format abhi bhi kaam karega.


## v3.1.2 fixes
- improved search matching and suggestions
- help command shows admin commands only to admins
- group /start and force-join flow now replies in user-scoped way
