# Learning Gap Analyzer

**Turn quiz results into timely, personal support.** Learning Gap Analyzer finds topic-level gaps, points each learner toward a useful next step, and gives faculty a class-wide view of where support can make a difference.

## Demo

1. Install the dependencies and start the app:

	```powershell
	python -m pip install -r requirements.txt
	python -m streamlit run app.py
	```

2. Open **Upload data** and select **Load sample data** for a cohort of 40 students across four engineering subjects.
3. Open **Student dashboard** and switch learners to see a progress profile, learning trend, topic priorities, and matched resources.
4. Open **Practice**, answer questions for a suggested topic, and submit. The new result is saved and reflected in the learner report.
5. Open **Placement Dashboard** for a preparation indicator, priority skill gaps, a personalized action plan, and achievement badges.
6. Open **Placement Prep** to practice a technical, HR/behavioral, or mixed mock interview for a target role, write answers, reflect on confidence, and review coaching notes.
7. Open **Class overview** to review performance groups, challenging topics, and the learner support list.

## What It Does

- Accepts CSV score data and validates required fields, dates, and mark ranges before saving to SQLite.
- Calculates subject and topic averages, then highlights topics for review.
- Matches learning resources to the learner's subject and topic.
- Builds practice quizzes from the included question bank and records submitted results.
- Summarizes career-preparation progress with a transparent readiness indicator, learner-specific next steps, skill gaps, achievements, and in-session mock-interview history.
- Provides placement interview practice with built-in role-specific questions, suggested answer approaches, confidence reflection, and optional AI-generated questions and coaching.
- Groups learners using KMeans clustering over subject performance for a class-level support view.
- Optionally generates additional practice questions with Anthropic Claude.

## Data Format

CSV uploads require these columns. `class`, `section`, and `branch` are optional learner details:

```text
student_id,name,subject,topic,marks_obtained,max_marks,quiz_date,class,section,branch
```

For example: `CS001,Ananya,DBMS,Normalization,8,10,2026-09-12,2nd Year,A,Computer Science`.
You can also add or update these details from **Upload data → Student details**. They appear on the student dashboard and in the searchable, filterable class roster. Older CSV files remain valid, and details are stored per student.

## Optional AI Questions

Set `ANTHROPIC_API_KEY` in your environment and enable **Add newly generated AI questions** on the Practice page to add five AI-generated questions, with correct answers and explanations. Without a key, built-in questions continue to work. Practice questions are shown five per page; after submitting the complete quiz, the answer review identifies missed questions and shows the correct answer and any available explanation. The AI prompt includes the selected subject and topic, not the student's name or score history.

## Placement Interview Practice

The **Placement Prep** page offers technical, HR/behavioral, and mixed interview rounds for software engineering, frontend, backend, and data analyst roles. Candidates answer a short mock interview one question at a time, self-rate confidence, and review suggested answer approaches and evaluation criteria. With `ANTHROPIC_API_KEY`, learners can opt in to AI-generated questions and coaching feedback. Only the selected role, interview questions, and submitted answers are sent for this feature; student names, IDs, and academic scores are not included. Interview responses and confidence ratings stay in the current browser session and are not saved to the academic score history.

## Placement Readiness Dashboard

The **Placement Dashboard** brings academic mastery, priority topics, interview confidence, student-profile completion, and achievement badges into one personalized view. Its preparation score is a transparent learning signal: academic mastery alone before a mock interview, then 60% academic mastery plus 40% of self-rated interview confidence after practice. It is not a placement probability or hiring prediction. Interview history and badges use the current browser session and are not written to academic scores or the database.

## Data and Methods

Scores and practice results are stored locally in `student_data.db`, which is excluded from Git. Topic levels use transparent score thresholds: below 40% is **Weak**, below 60% is **Needs Practice**, and 60% or higher is **Strong**. KMeans clustering is used for class grouping; it is an early-support signal, not a student diagnosis.

## Stack

Python · Streamlit · SQLite · pandas · scikit-learn · Plotly
