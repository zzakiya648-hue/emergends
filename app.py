import streamlit as st
from datetime import date

from db import init_db, query
from bots import (onboarding_reply, parse_done, save_intern, assign_task,
                  give_feedback, get_intern_by_email, latest_task)
from scheduler import start_scheduler, run_job, SCHEDULE_MINUTES

st.set_page_config(page_title="Internship Progress Assistant", page_icon="🎓", layout="wide")
init_db()


@st.cache_resource
def boot():
    return start_scheduler()


boot()

st.title("🎓 Internship Progress Assistant")
st.caption("Bot 1: Onboarding  →  Bot 2: Task + Email  →  Bot 3: Feedback  →  repeat till end date")

tab1, tab2, tab3 = st.tabs(["🤖 Bot 1 · Onboarding", "📝 Bot 3 · Progress & Feedback", "📊 Dashboard / Loop"])

# ------------------------------------------------------------------
# TAB 1 : BOT 1 (+ triggers Bot 2 first task)
# ------------------------------------------------------------------
with tab1:
    if "chat" not in st.session_state:
        st.session_state.chat = [(
            "assistant",
            "Vanakkam! 👋 Naan unga Internship Onboarding Bot. Welcome! "
            "Modhalla unga **name** sollunga, apram mathatha details kekkuren.",
        )]
        st.session_state.done = False

    for role, msg in st.session_state.chat:
        st.chat_message(role).write(msg)

    if st.session_state.done:
        st.success("Onboarding mudinjuchu ✅. Puthu intern add panna 'Reset chat' click pannunga.")
        if st.button("Reset chat"):
            del st.session_state["chat"]
            st.rerun()
    else:
        user = st.chat_input("Type here...", key="onb")
        if user:
            st.session_state.chat.append(("user", user))
            try:
                reply = onboarding_reply(st.session_state.chat)
                clean, parts = parse_done(reply)
                if parts:
                    try:
                        iid = save_intern(parts)
                        _, err = assign_task(iid)   # BOT 2 triggers
                        clean += (f"\n\n✅ Profile save aachu (Intern ID: {iid}). "
                                  "Bot 2 first task email anuppiyachu, inbox/spam check pannunga.")
                        if err:
                            clean += f"\n\n⚠️ Email anuppa mudiyala: {err}"
                        st.session_state.done = True
                    except Exception as e:
                        clean += f"\n\n⚠️ Details save panna mudiyala ({e}). Correct ah marupadi sollunga."
                st.session_state.chat.append(("assistant", clean))
            except Exception as e:
                st.session_state.chat.append(("assistant", f"⚠️ Error: {e}"))
            st.rerun()

# ------------------------------------------------------------------
# TAB 2 : BOT 3
# ------------------------------------------------------------------
with tab2:
    st.subheader("Unga progress report pannunga")
    email = st.text_input("Registered email").strip()
    intern = get_intern_by_email(email) if email else None

    if email and not intern:
        st.error("Indha email la intern illa. Bot 1 la first register pannunga.")
    if intern:
        task = latest_task(intern["id"])
        st.info(f"Hi {intern['name']}! Internship end date: {intern['end_date']}")
        if intern["completed"]:
            st.success("Unga internship mudinjuchu 🎉")
        elif not task:
            st.warning("Innum task assign aagala.")
        else:
            with st.expander(f"Current task (Task {task['week']} · deadline {task['deadline']})", expanded=True):
                st.text(task["description"])
            if task["status"] == "done":
                st.success("Indha task ku feedback already vanthuduchu. Next task email ku wait pannunga.")
            progress = st.text_area("Enna panninga? Enna problem vanthuchu?", height=160)
            if st.button("Submit progress", type="primary"):
                if len(progress.strip()) < 10:
                    st.warning("Konjam detail ah ezhudhunga.")
                else:
                    with st.spinner("Bot 3 feedback ezhudhudhu..."):
                        try:
                            text, score, err = give_feedback(intern["id"], progress)
                            st.markdown(f"### Score: {score}/10")
                            st.write(text)
                            st.caption("Feedback email um anuppiyachu." if not err else f"⚠️ Email error: {err}")
                        except Exception as e:
                            st.error(f"Error: {e}")

# ------------------------------------------------------------------
# TAB 3 : DASHBOARD + LOOP CONTROL
# ------------------------------------------------------------------
with tab3:
    st.subheader("Loop control")
    st.write(f"Bot 2 auto-repeat gap: **{SCHEDULE_MINUTES} minutes** (.env la `SCHEDULE_MINUTES`). "
             "End date vanthaa final report anuppi stop aagum.")
    if st.button("▶ Run next cycle now (demo)"):
        with st.spinner("Running..."):
            for line in run_job():
                st.write("•", line)

    st.subheader("Interns")
    interns = query("SELECT id,name,email,domain,start_date,end_date,completed FROM interns")
    st.dataframe(interns, use_container_width=True) if interns else st.write("Innum intern illa.")

    st.subheader("Tasks & scores")
    rows = query("""SELECT i.name, t.week, t.deadline, t.status, f.score
                    FROM tasks t JOIN interns i ON i.id=t.intern_id
                    LEFT JOIN feedback f ON f.task_id=t.id ORDER BY t.id DESC""")
    st.dataframe(rows, use_container_width=True) if rows else st.write("Innum task illa.")
