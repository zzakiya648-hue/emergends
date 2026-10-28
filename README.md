# Internship Progress Assistant (3 Bots + Email + Loop)

## Setup (once)
1. Python 3.10+ install pannunga.
2. `.env.example` ah copy panni `.env` nu rename pannunga, values fill pannunga:
   - GEMINI_API_KEY  -> aistudio.google.com/apikey
   - EMAIL_APP_PASSWORD -> Google Account > Security > 2-Step ON > App passwords
3. Run:
   - Windows: `run.bat` double click
   - Mac/Linux: `./run.sh`

## Demo flow
1. Tab 1: Bot 1 kitta details sollunga (unga own email kudunga) -> Bot 2 first task email anuppum
2. Tab 2: email enter panni progress submit -> Bot 3 feedback (app + email)
3. Tab 3: "Run next cycle now" -> Bot 2 next task (previous feedback use pannum). End date vanthaa final report.
   Auto loop: .env la SCHEDULE_MINUTES=2 vechu test pannalam.

## Files
db.py (SQLite) | llm.py (Gemini) | mailer.py (Gmail SMTP) | bots.py (3 bots)
scheduler.py (loop) | app.py (Streamlit UI)
