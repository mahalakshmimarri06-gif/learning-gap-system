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
5. Open **Class overview** to review performance groups, challenging topics, and the learner support list.

## What It Does

- Accepts CSV score data and validates required fields, dates, and mark ranges before saving to SQLite.
- Calculates subject and topic averages, then highlights topics for review.
- Matches learning resources to the learner's subject and topic.
- Builds practice quizzes from the included question bank and records submitted results.
- Groups learners using KMeans clustering over subject performance for a class-level support view.
- Optionally generates additional practice questions with Anthropic Claude.

## Data Format

CSV uploads need these columns:

```text
student_id,name,subject,topic,marks_obtained,max_marks,quiz_date
```

For example: `CS001,Ananya,DBMS,Normalization,8,10,2026-09-12`.

## Optional AI Questions

Set `ANTHROPIC_API_KEY` in your environment to enable AI-generated questions in the Practice page. This is opt-in; without a key, the built-in question bank continues to work. The AI prompt includes the selected subject and topic, not the student's name or score history.

## Data and Methods

Scores and practice results are stored locally in `student_data.db`, which is excluded from Git. Topic levels use transparent score thresholds: below 40% is **Weak**, below 60% is **Needs Practice**, and 60% or higher is **Strong**. KMeans clustering is used for class grouping; it is an early-support signal, not a student diagnosis.

## Stack

Python · Streamlit · SQLite · pandas · scikit-learn · Plotly
