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

def placement_readiness(academic_percent, interview_confidence=None):
    """Return a transparent preparation indicator, not a hiring prediction."""
    academic = max(0.0, min(100.0, float(academic_percent)))
    if interview_confidence is None:
        score = academic
        interview_percent = None
    else:
        confidence = max(1.0, min(5.0, float(interview_confidence)))
        interview_percent = round(confidence / 5 * 100, 1)
        score = academic * 0.6 + interview_percent * 0.4

    score = round(score)
    label = (
        "Strong preparation" if score >= 75
        else "Building momentum" if score >= 55
        else "Start with the fundamentals"
    )
    return {
        "score": score,
        "academic_percent": round(academic, 1),
        "interview_percent": interview_percent,
        "provisional": interview_percent is None,
        "label": label,
    }

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


# ---------------- PLACEMENT INTERVIEW PREP ----------------
INTERVIEW_ROLES = [
    "Software Engineer",
    "Frontend Developer",
    "Backend Developer",
    "Data Analyst",
]
INTERVIEW_FORMATS = ["Technical", "HR / Behavioral", "Mixed"]

_HR_INTERVIEW_QUESTIONS = [
    {
        "category": "Introduction",
        "question": "Tell me about yourself and what you are looking for in your first role.",
        "sample_answer": (
            "A clear 60-90 second answer connects your current studies, one relevant project, "
            "a strength supported by evidence, and why this role is your next step. Personalize "
            "the details rather than memorizing a script."
        ),
        "evaluation_criteria": "A concise introduction, relevant evidence, and a clear link to the role.",
    },
    {
        "category": "Behavioral",
        "question": "Tell me about a difficult problem you solved with a team.",
        "sample_answer": (
            "Use STAR: briefly describe the situation and your responsibility, explain the "
            "specific actions you took with the team, and finish with a measurable result and "
            "what you learned."
        ),
        "evaluation_criteria": "A specific example, clear personal contribution, teamwork, and an outcome.",
    },
    {
        "category": "Behavioral",
        "question": "Describe a time you received critical feedback. What did you do with it?",
        "sample_answer": (
            "Choose a real example. Explain the feedback without becoming defensive, the change "
            "you made, and how you checked whether that change improved your work."
        ),
        "evaluation_criteria": "Ownership, openness to learning, concrete action, and reflection.",
    },
    {
        "category": "Motivation",
        "question": "Why are you interested in this role, and what would you bring to the team?",
        "sample_answer": (
            "Connect a genuine interest in the role to one relevant project or skill. Name a "
            "specific way you can contribute while being honest about what you are still learning."
        ),
        "evaluation_criteria": "Role-specific motivation, relevant evidence, and realistic self-awareness.",
    },
    {
        "category": "Behavioral",
        "question": "How do you prioritize when you have several deadlines at the same time?",
        "sample_answer": (
            "Explain how you compare urgency, impact, and dependencies, then communicate trade-offs "
            "early. Give a real example and describe how you checked that the important work was completed."
        ),
        "evaluation_criteria": "A practical prioritization method, proactive communication, and an example.",
    },
]

_TECHNICAL_INTERVIEW_QUESTIONS = {
    "Software Engineer": [
        ("How would you explain the difference between a stack and a queue, and when would you use each?",
         "A stack is last-in, first-out and suits undo history or function calls. A queue is first-in, first-out and suits task scheduling or breadth-first search. I would choose based on the order the problem needs to process items.",
         "Accurate LIFO/FIFO definitions, examples, and a reason for the choice."),
        ("What is the time complexity of binary search, and what condition must the input meet?",
         "Binary search takes O(log n) time because it removes half the remaining search space each step. The input must be ordered, and the data structure must support efficient access to the middle element.",
         "Correct complexity, halving explanation, and the sorted-input requirement."),
        ("How do you approach debugging a bug you cannot reproduce consistently?",
         "I would gather the exact environment and inputs, inspect logs and telemetry, look for patterns, and add targeted instrumentation. Then I would form and test one hypothesis at a time, write a regression test, and verify the fix under the conditions that triggered the issue.",
         "A repeatable investigation, evidence-based hypotheses, and regression prevention."),
        ("What makes a useful automated test? Give an example from a project.",
         "A useful test checks one observable behavior with controlled inputs and a clear expected result. For example, a unit test for a validation function can cover a valid value, a boundary case, and invalid input without depending on a live database.",
         "Specific behavior, meaningful assertions, isolated setup, and edge cases."),
        ("What is the difference between a process and a thread?",
         "A process has its own address space and operating-system resources. Threads run within a process and share its memory, so they can communicate efficiently but require care around synchronization and shared state.",
         "Separate address spaces versus shared process memory, with a trade-off or example."),
    ],
    "Frontend Developer": [
        ("How would you make a form accessible to keyboard and screen-reader users?",
         "I would use semantic form controls, visible labels associated with inputs, logical keyboard order, clear focus states, and accessible error messages linked to their fields. I would test the flow with a keyboard and an accessibility checker.",
         "Semantic controls, labels, keyboard/focus support, and accessible validation."),
        ("What is the difference between client-side and server-side validation?",
         "Client-side validation gives users fast feedback, but it can be bypassed. Server-side validation is authoritative and must enforce the rules before accepting data. A robust form uses both and keeps the rules consistent.",
         "Correct distinction, security awareness, and a consistent user experience."),
        ("How would you investigate a page that is slow to render?",
         "I would measure first with browser performance tools, identify whether the bottleneck is JavaScript, rendering, network, or assets, and then address the biggest measured cost. I would re-measure and check that the change did not harm accessibility or behavior.",
         "Measurement before changes, a clear diagnostic process, and re-testing."),
        ("How do you keep a user interface usable on small screens?",
         "I would use responsive layouts, flexible sizing, readable typography, touch-sized controls, and content that reflows rather than requiring horizontal scrolling. I would test at narrow widths and with zoom, not just rely on a desktop preview.",
         "Responsive reflow, touch usability, readable content, and testing."),
        ("When would you use local component state versus shared application state?",
         "I would keep state local when only one component or a small subtree needs it. I would move it to a shared store or context when unrelated parts of the app need the same state, while keeping the source of truth clear.",
         "Scope state to its consumers and avoid unnecessary global state."),
    ],
    "Backend Developer": [
        ("What is the difference between authentication and authorization?",
         "Authentication establishes who a user is; authorization decides what that authenticated user may do. For example, signing in verifies identity, while a role or policy check decides whether the user can view a particular record.",
         "Correct distinction and a relevant example."),
        ("How would you design an API endpoint that creates a new resource?",
         "I would define the resource schema and validation, use an appropriate HTTP method such as POST, require authorization, return a clear status and representation, and consider duplicate requests, logging, and tests for success and failure cases.",
         "Validation, HTTP semantics, access control, response behavior, and tests."),
        ("Why use a database transaction, and when would you need one?",
         "A transaction groups related database changes so they commit together or roll back together. I would use one when a business operation changes multiple related records and partial completion would leave inconsistent data.",
         "Atomicity, consistency, and a concrete multi-step example."),
        ("How would you investigate an API endpoint with high latency?",
         "I would inspect latency metrics and traces to locate time spent in the application, database, and external services. Then I would verify the suspected cause with query plans or profiling, make a targeted change, and compare measurements under similar load.",
         "Observability, evidence-driven diagnosis, targeted fixes, and measured verification."),
        ("What is an index in a relational database, and what is its trade-off?",
         "An index is an auxiliary structure that can speed up lookups and sorting for selected columns. It uses storage and adds work to inserts, updates, and deletes, so I would choose indexes based on real query patterns.",
         "Lookup benefit, storage/write cost, and query-driven selection."),
    ],
    "Data Analyst": [
        ("How would you explain the difference between an inner join and a left join?",
         "An inner join returns rows that match in both tables. A left join keeps every row from the left table and adds matching right-table values where available, leaving nulls when there is no match.",
         "Correct outputs and treatment of unmatched rows."),
        ("How would you handle missing values before analyzing a dataset?",
         "I would first measure where values are missing and investigate why. Depending on the meaning and amount of missingness, I might correct the source, exclude a justified subset, or impute values, documenting the choice and checking how it affects conclusions.",
         "Diagnose first, select a justified method, document assumptions, and assess impact."),
        ("What is the difference between correlation and causation?",
         "Correlation measures how two variables move together; it does not prove that one causes the other. Confounding factors, reverse effects, or coincidence may explain the relationship. Causal claims need an appropriate experimental or causal-inference design.",
         "Correct definition and at least one reason correlation does not prove causation."),
        ("How would you present an unexpected result to a non-technical stakeholder?",
         "I would lead with the finding and its practical implication, show a clear visual with the right comparison, explain the data and assumptions in plain language, and be explicit about uncertainty and next steps.",
         "Audience-aware communication, transparent assumptions, and an actionable next step."),
        ("How would you check whether a dashboard metric is misleading?",
         "I would verify its definition and source, check filters, time windows, missing values, and denominators, and compare it with an independent calculation. I would document the assumptions and ask stakeholders whether the metric matches the decision they need to make.",
         "Metric definition, data quality, independent validation, and decision context."),
    ],
}

def interview_question_bank(role, interview_format, n=5):
    """Return curated placement interview questions and coaching guides."""
    if role not in INTERVIEW_ROLES:
        raise ValueError(f"Unsupported interview role: {role}.")
    if interview_format not in INTERVIEW_FORMATS:
        raise ValueError(f"Unsupported interview format: {interview_format}.")
    if n < 1:
        raise ValueError("The interview must contain at least one question.")

    questions = []
    if interview_format in ("HR / Behavioral", "Mixed"):
        questions.extend(_HR_INTERVIEW_QUESTIONS)
    if interview_format in ("Technical", "Mixed"):
        questions.extend(
            {
                "category": "Technical",
                "question": question,
                "sample_answer": sample_answer,
                "evaluation_criteria": evaluation_criteria,
            }
            for question, sample_answer, evaluation_criteria
            in _TECHNICAL_INTERVIEW_QUESTIONS[role]
        )
    if interview_format == "Mixed":
        questions = questions[::2] + questions[1::2]
    if n > len(questions):
        raise ValueError(f"Only {len(questions)} curated questions are available for this interview format.")
    return questions[:n]

def ai_is_configured():
    """Whether an Anthropic API key is available for optional AI features."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))

def ai_interview_questions(role, interview_format, n=5):
    """Generate interview questions with answer guides; None means AI is not configured."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    prompt = (
        f"Create exactly {n} original placement-interview questions for a student applying "
        f"for a {role} role. Interview format: {interview_format}. Return ONLY a JSON list. "
        "Each item must contain category, question, sample_answer, and evaluation_criteria. "
        "For behavioral questions, the sample answer should be a coaching structure, not a fabricated "
        "personal story. Keep answers accurate, concise, and suitable for a student or new graduate."
    )
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    response = client.messages.create(
        model=model,
        max_tokens=3500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    questions = json.loads(text)
    if not isinstance(questions, list) or len(questions) != n:
        raise ValueError(f"AI response must contain exactly {n} interview questions.")
    required = ["category", "question", "sample_answer", "evaluation_criteria"]
    result = []
    for item in questions:
        if not isinstance(item, dict) or any(
            not isinstance(item.get(field), str) or not item[field].strip()
            for field in required
        ):
            raise ValueError("AI response contains a question with missing coaching details.")
        result.append({field: item[field].strip() for field in required})
    return result

def ai_interview_feedback(role, question, answer, evaluation_criteria):
    """Give concise interview coaching; None means AI is not configured."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    if not answer.strip():
        raise ValueError("An interview answer is required for feedback.")
    if len(answer) > 4000:
        raise ValueError("Interview answers for AI feedback must be 4,000 characters or fewer.")
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    prompt = (
        f"Give constructive placement-interview coaching for a student applying for {role}.\n"
        f"Question: {question}\n"
        f"Candidate answer: {answer}\n"
        f"Evaluation criteria: {evaluation_criteria}\n"
        "Respond in three short sections: What worked, One improvement, Try saying it this way. "
        "Do not invent experience or facts; encourage the candidate to use truthful examples."
    )
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    response = client.messages.create(
        model=model,
        max_tokens=700,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()

def save_practice_result(sid, subject, topic, correct, total):
    with conn() as c:
        student = c.execute("SELECT name FROM students WHERE student_id=?", (sid,)).fetchone()
        if student is None:
            raise ValueError("Student record not found; practice result was not saved.")
        c.execute("INSERT INTO scores(student_id,subject,topic,marks_obtained,max_marks,quiz_date) VALUES (?,?,?,?,?,date('now'))",
                  (sid, subject, topic, correct, total))
