🚀 Course Search Bot v3.2

By Code Devil

A powerful Telegram Course Search Bot that allows users to instantly search and access hundreds of courses directly inside Telegram.
The bot is designed for fast search, smart suggestions, course management, and admin control, powered by Python + Telegram Bot API + Supabase (PostgreSQL).

---

📂 Project Structure

COURSE-SEARCH-BOT
│
├── __pycache__
├── .gitignore
├── .python-version
│
├── app.py
├── bot.py
├── config.py
├── csv_importer.py
├── db.py
├── handlers.py
├── keyboards.py
├── services.py
├── utils.py
│
├── render.yaml
├── requirements.txt
├── sample_courses.csv
└── README.md

File Description

File| Purpose
app.py| FastAPI server + bot startup
bot.py| Telegram bot initialization
config.py| Environment variables & settings
csv_importer.py| Import courses using CSV
db.py| Supabase/PostgreSQL database connection
handlers.py| Bot commands and message handlers
keyboards.py| Inline buttons and menu layouts
services.py| Core business logic (search, analytics, etc.)
utils.py| Helper utilities
render.yaml| Render deployment config
requirements.txt| Python dependencies
sample_courses.csv| Sample course data
README.md| Project documentation

---

✨ Features

🔎 Smart Course Search

Users can search courses in two ways:

Command Search

/search python

Direct Text Search

python course

The bot returns matching courses with interactive buttons.

---

💡 Smart Suggestions

If a user types a wrong keyword, the bot automatically suggests similar searches.

Example:

pythn

Suggestion:

Did you mean: python ?

---

📂 Categories

Courses are organized into categories like:

- Web Development
- Data Science
- AI / ML
- App Development
- DevOps
- Blockchain

Users can browse courses easily.

---

⭐ Featured Courses

Admins can mark courses as featured.

/feature <course_id>

---

🆕 Recently Added Courses

Users can view the latest courses.

/new

---

🔥 Trending Courses

Shows courses that are most searched or opened.

/trending

---

⭐ Bookmark Courses

Users can save courses to view later.

Button:

⭐ Save Course

View saved courses:

/saved

---

📩 Course Request System

Users can request missing courses.

/request course name

Example:

/request NextJS 15 Course

Admins can review these requests.

---

🔐 Force Subscribe System

Before using the bot, users must join required Telegram channels.

The bot automatically verifies membership.

---

💳 Paid Course Support

Supports paid courses with admin approval.

Admins can grant access:

/grant <user_id> <course_id>

---

👨‍💻 Admin Commands

These commands are admin-only.

Command| Description
"/addcourse"| Add new course
"/updatecourse"| Update course
"/deletecourse"| Delete course
"/restorecourse"| Restore deleted course
"/setthumb"| Set thumbnail
"/feature"| Mark course as featured
"/unfeature"| Remove featured
"/stats"| Bot analytics
"/requests"| View course requests
"/requestdone"| Mark request completed
"/broadcast"| Send message to all users
"/maintenance on"| Enable maintenance
"/maintenance off"| Disable maintenance
"/admin"| Admin panel

---

⚙️ Environment Variables

Create ".env" file.

Example:
PORT=10000
BOT_Name="Code Devil Course Link Bot"
BOT_TOKEN=your_bot_token
BOT_WELCOME_IMAGE=blob:https://web.telegram.org/54a2cef4-cf4a-4978-b869-95ce084b029c
ADMIN_IDS=123456789
SUPABASE_DB_URL=postgresql://user:password@host:port/db
MAIN_CHANNEL_URL=https://t.me/Code_Devil
PREMIUM_CHANNEL_LINK=https://t.me/xyzchannel
PLAYLISTS_URL=https://t.me/addlist/wTBxgyESacMwMDA1
PYTHON_VERSION=3.11.11
FORCE_SUB_CHANNELS=@Code_Devil,@Devil_Developee
FORCE_SUB_CHANNEL_URLS=https://t.me/Code_Devil,https://t.me/Devil_Developee
SUPPORT_CONTACT_URL=https://t.me/B_C_Admin_Bot
WHATSAPP_CHANNEL_URL=https://whatsapp.com/channel/0029VaacxeOKWEKsD2KdqR0U


PAGE_SIZE=5

---

🚀 Installation

Clone the repository

git clone https://github.com/your-repo/course-search-bot

Install dependencies

pip install -r requirements.txt

Run the bot

python app.py

---

🌐 Deployment

Supported platforms:

- Render
- Railway
- VPS
- Docker
- Termux

Use UptimeRobot to keep the service active 24/7.

---

📊 Database (Supabase)

Required tables:

courses
keywords
search_logs
purchases
course_requests
saved_courses
bot_settings

---

🛠 Tech Stack

- Python
- Telegram Bot API
- FastAPI
- Supabase PostgreSQL
- Async Programming

---

📢 Official Channels

Telegram

- https://t.me/Code_Devil
- https://t.me/Devil_Developee

WhatsApp Channel

- https://whatsapp.com/channel/0029VaacxeOKWEKsD2KdqR0U

YouTube

- https://www.youtube.com/@Devil_Coder

---

👑 Owner

Code Devil
https://t.me/code_devil24

---

⭐ Support

If you like this project:

- ⭐ Star the repository
- Share the bot with others
- Contribute improvements

Happy Learning 🚀