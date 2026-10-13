"""Database + analysis + recommendation + question logic (no Streamlit here)."""
import json
import os
import sqlite3
from pathlib import Path

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
DB = str(ROOT / "student_data.db")
REQUIRED = ["student_id", "name", "subject", "topic", "marks_obtained", "max_marks", "quiz_date"]
STUDENT_DETAILS = ["class", "section", "branch"]


# ---------------- DATABASE (Member 1) ----------------
def conn():
    return sqlite3.connect(DB)

def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS students(student_id TEXT PRIMARY KEY, name TEXT);
        CREATE TABLE IF NOT EXISTS scores(
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, subject TEXT, topic TEXT,
            marks_obtained REAL, max_marks REAL, quiz_date TEXT);
        CREATE TABLE IF NOT EXISTS resources(subject TEXT, topic TEXT, title TEXT, url TEXT, type TEXT);
        CREATE TABLE IF NOT EXISTS questions(
            subject TEXT, topic TEXT, question TEXT, option_a TEXT, option_b TEXT,
            option_c TEXT, option_d TEXT, correct_option TEXT, difficulty TEXT);
        """)
        student_columns = {
            row[1] for row in c.execute("PRAGMA table_info(students)").fetchall()
        }
        for column, sql_type in [
            ("class_name", "TEXT"),
            ("section", "TEXT"),
            ("branch", "TEXT"),
        ]:
            if column not in student_columns:
                c.execute(f"ALTER TABLE students ADD COLUMN {column} {sql_type}")

def validate_scores(df):
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    df = df.copy()
    for column in STUDENT_DETAILS:
        if column not in df.columns:
            df[column] = ""
    df = df[REQUIRED + STUDENT_DETAILS].dropna(subset=REQUIRED).copy()
    df["marks_obtained"] = pd.to_numeric(df["marks_obtained"], errors="coerce")
    df["max_marks"] = pd.to_numeric(df["max_marks"], errors="coerce")
    df["quiz_date"] = pd.to_datetime(df["quiz_date"], errors="coerce")
    df = df.dropna(subset=["marks_obtained", "max_marks", "quiz_date"])
    df = df[(df["max_marks"] > 0) & (df["marks_obtained"] >= 0) & (df["marks_obtained"] <= df["max_marks"])]
    df["student_id"] = df["student_id"].astype(str).str.strip().str.upper()
    for column in ["name", "subject", "topic"]:
        df[column] = df[column].astype(str).str.strip()
    for column in STUDENT_DETAILS:
        df[column] = df[column].fillna("").astype(str).str.strip()
    df = df[(df["student_id"] != "") & (df["name"] != "") & (df["subject"] != "") & (df["topic"] != "")]
    df["quiz_date"] = df["quiz_date"].dt.strftime("%Y-%m-%d")
    return df

def save_scores(df, replace=False):
    df = validate_scores(df)
    if df.empty:
        raise ValueError("No valid score rows found. Check dates, marks, and required fields.")
    with conn() as c:
        if replace:
            c.execute("DELETE FROM scores"); c.execute("DELETE FROM students")
        df[REQUIRED].drop(columns=["name"]).to_sql("scores", c, if_exists="append", index=False)
        records = df[["student_id", "name", *STUDENT_DETAILS]].drop_duplicates(
            subset=["student_id"], keep="last"
        )
        c.executemany(
            """
            INSERT INTO students(student_id, name, class_name, section, branch)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                name = excluded.name,
                class_name = CASE WHEN excluded.class_name != ''
                    THEN excluded.class_name ELSE students.class_name END,
                section = CASE WHEN excluded.section != ''
                    THEN excluded.section ELSE students.section END,
                branch = CASE WHEN excluded.branch != ''
                    THEN excluded.branch ELSE students.branch END
            """,
            [
                (row[0], row[1], row[2], row[3], row[4])
                for row in records.itertuples(index=False, name=None)
            ],
        )
    return len(df)

def load_reference_data():
    """Load resources + question bank CSVs into DB if tables are empty."""
    with conn() as c:
        resources_path = ROOT / "data" / "resources.csv"
        questions_path = ROOT / "data" / "question_bank.csv"
        if c.execute("SELECT COUNT(*) FROM resources").fetchone()[0] == 0 and resources_path.exists():
            pd.read_csv(resources_path).to_sql("resources", c, if_exists="append", index=False)
        if c.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 0 and questions_path.exists():
            pd.read_csv(questions_path).to_sql("questions", c, if_exists="append", index=False)

def all_scores():
    with conn() as c:
        return pd.read_sql(
            """
            SELECT s.*, st.name, st.class_name AS class, st.section, st.branch
            FROM scores s JOIN students st USING(student_id)
            """,
            c,
        )

def student_scores(sid):
    df = all_scores()
    return df[df.student_id == sid]

def students_list():
    with conn() as c:
        return pd.read_sql(
            """
            SELECT student_id, name, class_name AS class, section, branch
            FROM students ORDER BY student_id
            """,
            c,
        )

def update_student_details(student_id, student_class, section, branch):
    """Update a student's class, section, and branch without changing their scores."""
    with conn() as c:
        cursor = c.execute(
            """
            UPDATE students
            SET class_name = ?, section = ?, branch = ?
            WHERE student_id = ?
            """,
            (
                student_class.strip(),
                section.strip(),
                branch.strip(),
                student_id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"No student record found for {student_id}.")


# ---------------- ANALYSIS (Member 2) ----------------
def topic_performance(df):
    d = df.copy()
    d["percent"] = d.marks_obtained / d.max_marks * 100
    t = d.groupby(["subject", "topic"])["percent"].mean().round(1).reset_index()
    t["level"] = pd.cut(t["percent"], [-1, 40, 60, 100.1], labels=["Weak", "Needs Practice", "Strong"])
    return t.sort_values("percent")

def subject_performance(df):
    d = df.copy()
    d["percent"] = d.marks_obtained / d.max_marks * 100
    return d.groupby("subject")["percent"].mean().round(1).reset_index()

def trend(df):
    """Compare average of earlier half of quizzes with later half (by date)."""
    d = df.copy().sort_values("quiz_date")
    d["percent"] = d.marks_obtained / d.max_marks * 100
    if len(d) < 4:
        return "Not enough data", 0.0
    half = len(d) // 2
    diff = round(d.iloc[half:].percent.mean() - d.iloc[:half].percent.mean(), 1)
    label = "Improving" if diff > 3 else "Declining" if diff < -3 else "Stable"
    return label, diff

def cluster_students(df, k=3):
    """KMeans on each student's subject-wise average -> Strong / Average / Needs Support."""
    d = df.copy()
    d["percent"] = d.marks_obtained / d.max_marks * 100
    piv = d.pivot_table(index=["student_id", "name"], columns="subject", values="percent", aggfunc="mean").fillna(0)
    if piv.empty:
        return pd.DataFrame(columns=["student_id", "name", "group", "overall"])
    X = StandardScaler().fit_transform(piv.values)
    cluster_count = min(k, len(piv), len(pd.DataFrame(X).drop_duplicates()))
    if cluster_count < 2:
        piv["overall"] = piv.mean(axis=1).round(1)
        piv["group"] = piv["overall"].map(
            lambda score: "Needs Support" if score < 50 else "Average" if score < 75 else "Strong"
        )
        return piv.reset_index()
    piv["cluster"] = KMeans(n_clusters=cluster_count, n_init=10, random_state=42).fit_predict(X)
    piv["overall"] = piv.drop(columns="cluster").mean(axis=1).round(1)
    order = piv.groupby("cluster")["overall"].mean().sort_values().index.tolist()
    labels = ["Needs Support", "Average", "Strong"]
    names = {cluster: labels[index] for index, cluster in enumerate(order)}
    piv["group"] = piv["cluster"].map(names)
    return piv.drop(columns="cluster").reset_index()

def recommend_resources(weak_df, per_topic=3):
    with conn() as c:
        res = pd.read_sql("SELECT * FROM resources", c)
    out = []
    for r in weak_df.itertuples():
        m = res[(res.subject == r.subject) & (res.topic == r.topic)].head(per_topic)
        out.append(m)
    return pd.concat(out) if out else pd.DataFrame()


# ---------------- PRACTICE QUESTIONS (Member 2) ----------------
def bank_questions(subject, topic, n=5):
    with conn() as c:
        q = pd.read_sql("SELECT * FROM questions WHERE subject=? AND topic=?", c, params=(subject, topic))
    return q.sample(min(n, len(q))) if len(q) else q

def ai_questions(subject, topic, n=3):
    """Generate MCQs with Claude. Returns None when AI is not configured."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    prompt = (
        f"Create {n} multiple-choice questions for an engineering student on '{topic}' in {subject}. "
        "Return ONLY a JSON list. Each item must have: question, option_a, option_b, option_c, "
        "option_d, correct_option (one of A,B,C,D), explanation (a concise explanation of why "
        "the correct option is right), and difficulty (easy/medium). Ensure exactly one correct option."
    )
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    msg = client.messages.create(
        model=model,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    questions = json.loads(text)
    if not isinstance(questions, list):
        raise ValueError("AI response must be a JSON list of questions.")

    required = [
        "question", "option_a", "option_b", "option_c", "option_d",
        "correct_option", "explanation", "difficulty",
    ]
    df = pd.DataFrame(questions)
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"AI response is missing question fields: {', '.join(missing)}.")
    if len(df) != n:
        raise ValueError(f"AI response returned {len(df)} questions; expected {n}.")
    for column in required:
        df[column] = df[column].astype(str).str.strip()
    df["correct_option"] = df["correct_option"].str.upper()
    if df.empty or (df[required] == "").any().any() or not df["correct_option"].isin(list("ABCD")).all():
        raise ValueError("AI response contains incomplete questions or an invalid correct option.")
    df["subject"], df["topic"] = subject, topic
    return df

def save_practice_result(sid, subject, topic, correct, total):
    with conn() as c:
        student = c.execute("SELECT name FROM students WHERE student_id=?", (sid,)).fetchone()
        if student is None:
            raise ValueError("Student record not found; practice result was not saved.")
        c.execute("INSERT INTO scores(student_id,subject,topic,marks_obtained,max_marks,quiz_date) VALUES (?,?,?,?,?,date('now'))",
                  (sid, subject, topic, correct, total))
