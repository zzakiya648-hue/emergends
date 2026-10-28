"""3 bots:
Bot 1 - Onboarding (details + rules)
Bot 2 - Task generator + email
Bot 3 - Feedback
"""
import os
import re
from datetime import date, timedelta
from dotenv import load_dotenv

from db import query, execute
from llm import ask
from mailer import send_email

load_dotenv()
TASK_DAYS = int(os.getenv("TASK_DAYS", "7"))

# ============================================================
# BOT 1 : ONBOARDING
# ============================================================
ONBOARD_PROMPT = """You are Bot 1, a friendly onboarding assistant for an internship program.
Today's date is {today}.
You are chatting with a new intern. Reply ONLY with your next message (never write the intern's lines).

Collect these details, one or two at a time, in a friendly tone:
name, email, domain (e.g. Web Dev / AI / Data), skills, goals, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD).

Also briefly explain the internship rules:
- Bot 2 emails you tasks with instructions and a deadline.
- After the deadline you come to the Progress tab and report your progress.
- Bot 3 gives you feedback and a score, and the next task adapts to it.
- This repeats until your internship end date.

When you have ALL 7 details, summarise them and end your message with a final line EXACTLY like this
(no extra text on that line, use '-' if something is unknown, no '|' inside values):
DONE|name|email|domain|skills|goals|start_date|end_date
"""


def onboarding_reply(chat):
    transcript = "\n".join(
        f"{'Intern' if r == 'user' else 'Bot 1'}: {m}" for r, m in chat
    )
    return ask(ONBOARD_PROMPT.format(today=date.today().isoformat()),
               transcript + "\nBot 1:")


def parse_done(reply):
    """Returns (clean_reply, parts or None)."""
    for line in reply.splitlines():
        if line.strip().startswith("DONE|"):
            parts = [p.strip() for p in line.strip().split("|")]
            clean = reply.replace(line, "").strip()
            if len(parts) == 8:
                return clean, parts
    return reply, None


def save_intern(parts):
    _, name, email, domain, skills, goals, start, end = parts
    if "@" not in email:
        raise ValueError("Email sariya illa")
    date.fromisoformat(start)
    date.fromisoformat(end)
    return execute(
        "INSERT INTO interns (name,email,domain,skills,goals,start_date,end_date) "
        "VALUES (?,?,?,?,?,?,?)",
        (name, email.lower(), domain, skills, goals, start, end),
    )


def get_intern_by_email(email):
    rows = query("SELECT * FROM interns WHERE lower(email)=? ORDER BY id DESC LIMIT 1",
                 (email.strip().lower(),))
    return rows[0] if rows else None


# ============================================================
# BOT 2 : TASK + EMAIL
# ============================================================
TASK_PROMPT = """You are Bot 2, a mentor who assigns internship tasks and emails them.
Write the next task email for the intern. Include:
greeting, task title, task description, step-by-step instructions, helpful resources, deadline,
and how to submit progress (open the Progress tab of the Internship App and enter your email).
Adapt using the previous results:
- good scores -> slightly harder, more challenging task
- weak scores -> simpler, more supportive task, mention what to improve
- previous task not submitted -> politely remind them
Plain text only, no markdown symbols. Sign off as 'Internship Mentor Bot'."""


def latest_task(intern_id):
    rows = query("SELECT * FROM tasks WHERE intern_id=? ORDER BY id DESC LIMIT 1",
                 (intern_id,))
    return rows[0] if rows else None


def assign_task(intern_id):
    """Generates next task, saves it, emails it. Returns (body, email_error or None)."""
    intern = query("SELECT * FROM interns WHERE id=?", (intern_id,))[0]
    past = query(
        """SELECT t.week, t.status, f.feedback_text, f.score
           FROM tasks t LEFT JOIN feedback f ON f.task_id=t.id
           WHERE t.intern_id=? ORDER BY t.id DESC LIMIT 3""", (intern_id,))
    week = len(query("SELECT id FROM tasks WHERE intern_id=?", (intern_id,))) + 1
    end = date.fromisoformat(intern["end_date"])
    deadline = min(date.today() + timedelta(days=TASK_DAYS), end)
    days_left = (end - date.today()).days

    history = "None (this is the first task)" if not past else "\n".join(
        f"Week {p['week']}: status={p['status']}, score={p['score']}, feedback={p['feedback_text']}"
        for p in past
    )
    prompt = (
        f"Intern: {intern['name']}\nDomain: {intern['domain']}\n"
        f"Skills: {intern['skills']}\nGoals: {intern['goals']}\n"
        f"Task number: {week}\nDeadline: {deadline.isoformat()}\n"
        f"Days left in internship: {days_left}\n"
        f"Previous results:\n{history}"
    )
    body = ask(TASK_PROMPT, prompt)
    execute("INSERT INTO tasks (intern_id,week,description,deadline) VALUES (?,?,?,?)",
            (intern_id, week, body, deadline.isoformat()))
    err = None
    try:
        send_email(intern["email"], f"Internship Task {week} - {intern['domain']}", body)
    except Exception as e:  # app crash aaga koodadhu
        err = str(e)
    return body, err


# ============================================================
# BOT 3 : FEEDBACK
# ============================================================
FEEDBACK_PROMPT = """You are Bot 3, a supportive but honest feedback mentor.
Given the task and the intern's progress report, write feedback with:
Strengths, Areas to improve, Next steps, and a score out of 10.
Be specific to what the intern wrote. If the report is vague, say so kindly.
Plain text. The LAST line must be exactly: SCORE|<integer 0-10>"""


def give_feedback(intern_id, reply):
    """Returns (feedback_text, score, email_error or None)."""
    task = latest_task(intern_id)
    if not task:
        raise ValueError("Indha intern ku innum task assign aagala")
    intern = query("SELECT * FROM interns WHERE id=?", (intern_id,))[0]
    raw = ask(FEEDBACK_PROMPT, f"Task:\n{task['description']}\n\nIntern progress report:\n{reply}")
    m = re.search(r"SCORE\|\s*(\d+)", raw)
    score = min(int(m.group(1)), 10) if m else 0
    text = re.sub(r"SCORE\|\s*\d+", "", raw).strip()
    execute("INSERT INTO feedback (task_id,intern_reply,feedback_text,score) VALUES (?,?,?,?)",
            (task["id"], reply, text, score))
    execute("UPDATE tasks SET status='done' WHERE id=?", (task["id"],))
    err = None
    try:
        send_email(intern["email"], f"Feedback for Task {task['week']} (Score {score}/10)", text)
    except Exception as e:
        err = str(e)
    return text, score, err


# ============================================================
# FINAL REPORT (loop mudiyum bodhu)
# ============================================================
def final_report(intern):
    rows = query(
        """SELECT t.week, f.score, f.feedback_text FROM tasks t
           LEFT JOIN feedback f ON f.task_id=t.id WHERE t.intern_id=? ORDER BY t.week""",
        (intern["id"],))
    scores = [r["score"] for r in rows if r["score"] is not None]
    avg = round(sum(scores) / len(scores), 1) if scores else 0
    summary = ask(
        "Write a short, warm internship completion email (plain text) with highlights, "
        "overall performance and encouragement. Sign off as 'Internship Mentor Bot'.",
        f"Intern: {intern['name']}, domain: {intern['domain']}, average score: {avg}/10\n"
        + "\n".join(f"Week {r['week']}: score={r['score']}" for r in rows),
    )
    return summary
