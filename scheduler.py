"""LOOP: Bot 2 ah repeat panna vekkum. today >= end_date aana stop + final report."""
import os
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from db import query, execute
from bots import assign_task, final_report
from mailer import send_email

load_dotenv()
SCHEDULE_MINUTES = int(os.getenv("SCHEDULE_MINUTES", "10080"))  # 7 days


def run_job():
    """Returns list of log lines (UI la kaata)."""
    log = []
    for intern in query("SELECT * FROM interns WHERE completed=0"):
        if date.today() >= date.fromisoformat(intern["end_date"]):
            try:
                send_email(intern["email"], "Internship Completed 🎉", final_report(intern))
                log.append(f"{intern['name']}: internship mudinjuchu, final report anuppiyachu")
            except Exception as e:
                log.append(f"{intern['name']}: final email error - {e}")
            execute("UPDATE interns SET completed=1 WHERE id=?", (intern["id"],))
        else:
            try:
                _, err = assign_task(intern["id"])
                log.append(f"{intern['name']}: next task assign aachu" +
                           (f" (email error: {err})" if err else " + email sent"))
            except Exception as e:
                log.append(f"{intern['name']}: error - {e}")
    return log


def start_scheduler():
    s = BackgroundScheduler()
    s.add_job(run_job, "interval", minutes=SCHEDULE_MINUTES, id="loop")
    s.start()
    return s
