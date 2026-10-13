from html import escape
from pathlib import Path
from uuid import uuid4

import pandas as pd
import plotly.express as px
import streamlit as st

import core


ROOT = Path(__file__).resolve().parent
LEVEL_COLORS = {"Weak": "#d96b54", "Needs Practice": "#d6a13e", "Strong": "#3c8064"}
GROUP_COLORS = {"Needs Support": "#d96b54", "Average": "#d6a13e", "Strong": "#3c8064"}

st.set_page_config(page_title="Learning Gap Analyzer", page_icon="🎓", layout="wide")
st.markdown(f"<style>{(ROOT / 'style.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
core.init_db()
core.load_reference_data()


def page_header(kicker, title, description):
    st.markdown(
        f'<div class="page-header"><div class="eyebrow">{escape(kicker)}</div>'
        f'<h1>{escape(title)}</h1><p>{escape(description)}</p></div>',
        unsafe_allow_html=True,
    )


def polish_chart(fig, height=340):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin={"l": 12, "r": 12, "t": 42, "b": 12},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "DM Sans, sans-serif", "color": "#647168", "size": 12},
        legend={"orientation": "h", "y": -0.22, "title": {"text": ""}},
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e9eee9", zeroline=False, title=None)
    fig.update_yaxes(showgrid=False, zeroline=False, title=None)
    return fig


students = core.students_list()
page_names = [
    "Student dashboard",
    "Practice",
    "Placement Dashboard",
    "Placement Prep",
    "Class overview",
    "Upload data",
]
default_page = "Student dashboard" if not students.empty else "Upload data"

with st.sidebar:
    st.markdown(
        '<div class="brand-lockup"><span class="brand-symbol">LG</span>'
        '<div><strong>Learning Gap</strong><span>ANALYZER</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sidebar-label">WORKSPACE</div>', unsafe_allow_html=True)
    page = st.radio("Workspace", page_names, index=page_names.index(default_page), label_visibility="collapsed")
    st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-label">LEARNER DATA</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sidebar-count"><strong>{len(students):02}</strong><span>students in view</span></div>', unsafe_allow_html=True)
    st.caption("Progress signals update when new quiz results are saved.")


def pick_student():
    labels = [f"{row.student_id} · {row.name}" for row in students.itertuples()]
    selected = st.sidebar.selectbox("Student", labels, label_visibility="visible")
    return selected.split(" · ", 1)[0]


if page == "Upload data":
    page_header("DATA INTAKE", "Performance data", "Bring quiz results into one clear view. Upload a class CSV or explore with the sample cohort.")
    existing = core.all_scores()
    learners = core.students_list()
    metrics = st.columns(3)
    metrics[0].metric("Score records", f"{len(existing):,}")
    metrics[1].metric("Students", f"{len(learners):,}")
    metrics[2].metric("Subjects", f"{existing.subject.nunique() if not existing.empty else 0}")

    left, right = st.columns([1.25, 0.75], gap="large")
    with left, st.container(border=True):
        st.markdown("#### Import a score file")
        st.caption(
            "Required: student_id, name, subject, topic, marks_obtained, max_marks, quiz_date. "
            "Optional student details: class, section, branch."
        )
        uploaded = st.file_uploader("Choose CSV file", type=["csv"], label_visibility="collapsed")
        replace = st.checkbox("Replace current score data", value=False)
        if st.button("Import scores", type="primary", disabled=uploaded is None, use_container_width=True):
            try:
                count = core.save_scores(pd.read_csv(uploaded), replace=replace)
                st.success(f"Imported {count:,} valid score records.")
            except Exception as error:
                st.error(f"Could not import this file: {error}")
        st.download_button(
            "Download CSV template",
            pd.DataFrame(columns=core.REQUIRED + core.STUDENT_DETAILS).to_csv(index=False),
            "learning_gap_template.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with right, st.container(border=True):
        st.markdown("#### Start with the sample cohort")
        st.caption("40 learners · 4 subjects · 16 topics · two quiz rounds")
        st.markdown('<div class="sample-mark">40<span>LEARNERS</span></div>', unsafe_allow_html=True)
        if st.button("Load sample data", use_container_width=True):
            count = core.save_scores(pd.read_csv(ROOT / "data" / "sample_scores.csv"), replace=True)
            st.success(f"Loaded {count:,} sample score records.")
            st.rerun()

    with st.container(border=True):
        st.markdown("#### Student details")
        st.caption("Add or update a learner's class, section, and branch. Score history is not changed.")
        if students.empty:
            st.info("Import a score file or load the sample cohort before adding student details.")
        else:
            details_by_student = students.set_index("student_id")
            detail_sid = st.selectbox(
                "Student",
                students.student_id.tolist(),
                format_func=lambda student_id: (
                    f"{student_id} · {details_by_student.loc[student_id, 'name']}"
                ),
                key="student_details_selector",
            )
            detail_record = details_by_student.loc[detail_sid]
            with st.form("student_details_form"):
                detail_columns = st.columns(3)
                with detail_columns[0]:
                    student_class = st.text_input(
                        "Class",
                        value="" if pd.isna(detail_record["class"]) else str(detail_record["class"]),
                        placeholder="e.g. 2nd Year",
                    )
                with detail_columns[1]:
                    section = st.text_input(
                        "Section",
                        value="" if pd.isna(detail_record["section"]) else str(detail_record["section"]),
                        placeholder="e.g. A",
                    )
                with detail_columns[2]:
                    branch = st.text_input(
                        "Branch",
                        value="" if pd.isna(detail_record["branch"]) else str(detail_record["branch"]),
                        placeholder="e.g. Computer Science",
                    )
                if st.form_submit_button("Save student details", type="primary"):
                    try:
                        core.update_student_details(detail_sid, student_class, section, branch)
                    except Exception as error:
                        st.error(f"Could not update student details: {error}")
                    else:
                        st.success(f"Updated details for {detail_record['name']}.")

    st.markdown('<div class="section-heading"><div><span class="eyebrow">LATEST IMPORT</span><h2>Score records</h2></div></div>', unsafe_allow_html=True)
    existing = core.all_scores()
    if existing.empty:
        st.info("No scores yet. Import a CSV or load the sample cohort to get started.")
    else:
        st.dataframe(existing.head(100), use_container_width=True, hide_index=True)

elif page == "Student dashboard":
    if students.empty:
        st.warning("No learner data found. Load sample data or import a CSV to continue.")
        st.stop()

    sid = pick_student()
    df = core.student_scores(sid)
    name = str(df.name.iloc[0])
    student_record = students.loc[students.student_id == sid].iloc[0]
    topics = core.topic_performance(df)
    subjects = core.subject_performance(df)
    trend_label, trend_delta = core.trend(df)
    weak = topics[topics.level == "Weak"]
    needs = topics[topics.level == "Needs Practice"]
    focus = pd.concat([weak, needs]).sort_values("percent")
    average = subjects.percent.mean()

    page_header("LEARNER PROFILE", name, f"{sid} · Individual progress and practical next steps")
    profile_details = [
        ("Class", student_record["class"]),
        ("Section", student_record["section"]),
        ("Branch", student_record["branch"]),
    ]
    detail_badges = "".join(
        f'<span><strong>{label}</strong>{escape(str(value)) if pd.notna(value) and str(value).strip() else "Not set"}</span>'
        for label, value in profile_details
    )
    st.markdown(f'<div class="student-meta">{detail_badges}</div>', unsafe_allow_html=True)
    top = st.columns(4)
    top[0].metric("Average", f"{average:.1f}%")
    top[1].metric("Weak topics", len(weak))
    top[2].metric("Practice topics", len(needs))
    top[3].metric("Trend", f"{trend_delta:+.1f}%", trend_label)

    if not focus.empty:
        first = focus.iloc[0]
        st.markdown(
            f'<div class="next-step"><span class="next-step-label">NEXT BEST STEP</span>'
            f'<strong>Spend a little time on {escape(str(first.topic))}</strong>'
            f'<span>{escape(str(first.subject))} · current average {first.percent:.1f}%</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.success("Every tracked topic is currently in the strong range. Keep the momentum going.")

    chart_left, chart_right = st.columns(2, gap="large")
    with chart_left, st.container(border=True):
        st.markdown("#### Subject mastery")
        st.caption("Average score by subject")
        subject_fig = px.bar(
            subjects.sort_values("percent"), x="percent", y="subject", orientation="h",
            range_x=[0, 100], color="percent", color_continuous_scale=[[0, "#d96b54"], [0.6, "#d6a13e"], [1, "#3c8064"]],
        )
        subject_fig.update_coloraxes(showscale=False)
        st.plotly_chart(polish_chart(subject_fig, 300), use_container_width=True, config={"displayModeBar": False})

    with chart_right, st.container(border=True):
        st.markdown("#### Skill balance")
        st.caption("A wider shape means more even performance")
        radar = px.line_polar(subjects, r="percent", theta="subject", line_close=True, range_r=[0, 100])
        radar.update_traces(line_color="#3c8064", fill="toself", fillcolor="rgba(60,128,100,0.16)", marker={"size": 7})
        st.plotly_chart(polish_chart(radar, 300), use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="section-heading"><div><span class="eyebrow">TOPIC DETAIL</span><h2>Where to focus</h2></div></div>', unsafe_allow_html=True)
    topic_fig = px.bar(
        topics, x="percent", y="topic", color="level", orientation="h", facet_col="subject", facet_col_wrap=2,
        range_x=[0, 100], color_discrete_map=LEVEL_COLORS,
    )
    topic_fig.for_each_annotation(lambda annotation: annotation.update(text=annotation.text.split("=")[-1]))
    topic_fig.update_layout(bargap=0.34)
    topic_fig.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(polish_chart(topic_fig, 560), use_container_width=True, config={"displayModeBar": False})

    if not focus.empty:
        section_left, section_right = st.columns([1, 1.3], gap="large")
        with section_left:
            st.markdown("#### Improvement plan")
            st.dataframe(focus, use_container_width=True, hide_index=True)
            st.download_button("Export progress report", topics.to_csv(index=False), f"{sid}_report.csv", mime="text/csv")
        with section_right:
            st.markdown("#### Recommended learning resources")
            resources = core.recommend_resources(focus)
            if resources.empty:
                st.caption("No linked resources are available for these topics yet.")
            else:
                for (subject, topic), group in resources.groupby(["subject", "topic"], sort=False):
                    with st.expander(f"{subject} · {topic}"):
                        for resource in group.itertuples():
                            st.markdown(f"[{resource.title}]({resource.url}) · {resource.type}")

elif page == "Placement Dashboard":
    if students.empty:
        st.warning("No learner data found. Load sample data or import a CSV to continue.")
        st.stop()

    sid = pick_student()
    learner = students.loc[students.student_id == sid].iloc[0]
    learner_scores = core.student_scores(sid)
    topic_summary = core.topic_performance(learner_scores)
    subject_summary = core.subject_performance(learner_scores)
    academic_average = float(subject_summary.percent.mean()) if not subject_summary.empty else 0.0
    focus_topics = topic_summary[topic_summary.level != "Strong"].sort_values("percent")

    interview_history = st.session_state.get(f"placement_interview_history_{sid}", [])
    interview_ratings = [
        rating
        for attempt in interview_history
        for rating in attempt["ratings"]
    ]
    average_interview_confidence = (
        sum(interview_ratings) / len(interview_ratings) if interview_ratings else None
    )
    readiness = core.placement_readiness(academic_average, average_interview_confidence)

    profile_fields = [learner["class"], learner["section"], learner["branch"]]
    profile_completion = round(
        sum(pd.notna(value) and str(value).strip() != "" for value in profile_fields)
        / len(profile_fields)
        * 100
    )
    page_header(
        "CAREER READINESS",
        "Your placement dashboard",
        "Turn learning progress into a focused placement-preparation plan. Your readiness score is a study guide, not a hiring prediction.",
    )

    score_column, status_column = st.columns([1, 1.4], gap="large")
    with score_column, st.container(border=True):
        st.markdown("#### Placement readiness")
        st.metric("Preparation score", f"{readiness['score']} / 100", readiness["label"])
        st.progress(readiness["score"] / 100)
        if readiness["provisional"]:
            st.caption(
                "Provisional score: currently based on academic mastery. Complete a mock interview "
                "to include interview confidence (60% academic mastery + 40% interview confidence)."
            )
        else:
            st.caption(
                "Based on 60% academic mastery and 40% of your self-rated mock-interview confidence. "
                "It is not a placement probability."
            )

    with status_column, st.container(border=True):
        st.markdown("#### Your preparation snapshot")
        component_columns = st.columns(3)
        component_columns[0].metric("Academic mastery", f"{academic_average:.1f}%")
        component_columns[1].metric(
            "Interview confidence",
            f"{average_interview_confidence:.1f} / 5" if average_interview_confidence is not None else "Not started",
        )
        component_columns[2].metric("Student profile", f"{profile_completion}%")
        st.caption(
            f"{learner['name']} · {learner['class'] or 'Class not set'} · "
            f"Section {learner['section'] or 'not set'} · {learner['branch'] or 'Branch not set'}"
        )

    overview_columns = st.columns(3)
    overview_columns[0].metric("Skill gaps to work on", f"{len(focus_topics)}")
    overview_columns[1].metric("Strong topics", f"{int((topic_summary.level == 'Strong').sum())}")
    overview_columns[2].metric("Mock interviews", f"{len(interview_history)}")

    st.markdown(
        '<div class="section-heading"><div><span class="eyebrow">YOUR ROADMAP</span>'
        '<h2>Next steps to move forward</h2></div></div>',
        unsafe_allow_html=True,
    )
    action_columns = st.columns(3, gap="medium")
    if not focus_topics.empty:
        first_gap = focus_topics.iloc[0]
        action_columns[0].markdown(
            f'<div class="career-action"><span>01 · SKILL BUILDING</span>'
            f'<strong>Strengthen {escape(str(first_gap.topic))}</strong>'
            f'<p>{escape(str(first_gap.subject))} is currently at {first_gap.percent:.1f}%. '
            f'Practice the fundamentals and try a short quiz.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        action_columns[0].markdown(
            '<div class="career-action"><span>01 · SKILL BUILDING</span>'
            '<strong>Keep your skills sharp</strong>'
            '<p>All tracked topics are strong. Continue reviewing concepts and solving new problems.</p></div>',
            unsafe_allow_html=True,
        )

    if not interview_history:
        interview_action = "Start your first mock interview"
        interview_description = "Practice explaining your approach and build confidence one answer at a time."
    elif average_interview_confidence is not None and average_interview_confidence < 4:
        interview_action = "Practice speaking with confidence"
        interview_description = "Try another round and support each answer with a specific example or clear reasoning."
    else:
        interview_action = "Try a different interview round"
        interview_description = "Broaden your preparation by switching between technical and HR / behavioral questions."
    action_columns[1].markdown(
        f'<div class="career-action"><span>02 · INTERVIEW PRACTICE</span>'
        f'<strong>{escape(interview_action)}</strong>'
        f'<p>{escape(interview_description)}</p></div>',
        unsafe_allow_html=True,
    )

    missing_profile_fields = [
        label for label, value in zip(["class", "section", "branch"], profile_fields)
        if pd.isna(value) or not str(value).strip()
    ]
    if missing_profile_fields:
        profile_action = "Complete your learner profile"
        profile_description = f"Add your {', '.join(missing_profile_fields)} details from Upload data."
    else:
        profile_action = "Profile ready"
        profile_description = "Your class, section, and branch are filled in for a complete learner profile."
    action_columns[2].markdown(
        f'<div class="career-action"><span>03 · PROFILE</span>'
        f'<strong>{escape(profile_action)}</strong>'
        f'<p>{escape(profile_description)}</p></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-heading"><div><span class="eyebrow">MILESTONES</span>'
        '<h2>Achievements</h2></div></div>',
        unsafe_allow_html=True,
    )
    achievements = [
        (
            "Profile complete",
            profile_completion == 100,
            "Class, section, and branch are all set.",
            "Add your class, section, and branch.",
        ),
        (
            "First interview",
            len(interview_history) > 0,
            f"{len(interview_history)} mock interview(s) completed.",
            "Complete your first mock interview.",
        ),
        (
            "Confident communicator",
            average_interview_confidence is not None and average_interview_confidence >= 4,
            "Average interview confidence is 4 out of 5 or higher.",
            "Practice until your answer confidence reaches 4 out of 5.",
        ),
        (
            "Topic champion",
            len(topic_summary) > 0 and focus_topics.empty,
            "All tracked topics are currently in the strong range.",
            "Build every tracked topic into the strong range.",
        ),
    ]
    badge_columns = st.columns(4, gap="small")
    for column, (name, earned, description, next_step) in zip(badge_columns, achievements):
        icon = "★" if earned else "○"
        detail = description if earned else next_step
        column.markdown(
            f'<div class="achievement-card{" earned" if earned else ""}">'
            f'<span class="achievement-icon">{icon}</span>'
            f'<strong>{escape(name)}</strong><p>{escape(detail)}</p>'
            f'<small>{"UNLOCKED" if earned else "IN PROGRESS"}</small></div>',
            unsafe_allow_html=True,
        )

    progress_left, progress_right = st.columns([1.2, 0.8], gap="large")
    with progress_left, st.container(border=True):
        st.markdown("#### Skill map")
        st.caption("Subject-level averages from your saved quiz results.")
        subject_chart = px.bar(
            subject_summary.sort_values("percent"),
            x="percent",
            y="subject",
            orientation="h",
            range_x=[0, 100],
            color="percent",
            color_continuous_scale=[[0, "#d96b54"], [0.6, "#d6a13e"], [1, "#3c8064"]],
            text="percent",
        )
        subject_chart.update_traces(texttemplate="%{text:.0f}%", textposition="outside", cliponaxis=False)
        subject_chart.update_coloraxes(showscale=False)
        st.plotly_chart(polish_chart(subject_chart, 300), use_container_width=True, config={"displayModeBar": False})

    with progress_right, st.container(border=True):
        st.markdown("#### Priority topics")
        if focus_topics.empty:
            st.success("No priority gaps right now. Keep practicing to maintain your progress.")
        else:
            for gap in focus_topics.head(5).itertuples():
                st.markdown(
                    f'<div class="gap-row"><span>{escape(str(gap.subject))} · {escape(str(gap.topic))}</span>'
                    f'<strong>{gap.percent:.1f}%</strong></div>',
                    unsafe_allow_html=True,
                )
            if len(focus_topics) > 5:
                st.caption(f"Showing 5 of {len(focus_topics)} topics that need practice.")

    if interview_history:
        st.markdown("#### Interview practice history")
        history_rows = [
            {
                "Attempt": index,
                "Role": attempt["role"],
                "Format": attempt["format"],
                "Questions": len(attempt["ratings"]),
                "Average confidence": round(sum(attempt["ratings"]) / len(attempt["ratings"]), 1),
            }
            for index, attempt in enumerate(interview_history, start=1)
        ]
        st.dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)
        st.caption("Interview history and badges are held in the current browser session.")
    else:
        st.info("Complete a round in Placement Prep to add interview confidence and history to this dashboard.")

elif page == "Practice":
    if students.empty:
        st.warning("No learner data found. Load sample data or import a CSV to continue.")
        st.stop()

    sid = pick_student()
    df = core.student_scores(sid)
    focus = core.topic_performance(df)
    focus = focus[focus.level != "Strong"].reset_index(drop=True)
    page_header("PRACTICE LAB", "Practice with purpose", "Short, focused checks built around topics that need another look.")
    if focus.empty:
        st.success("No topics currently need extra practice.")
        st.stop()

    choice = st.selectbox(
        "Choose a topic",
        options=list(range(len(focus))),
        format_func=lambda index: f"{focus.iloc[index].subject} · {focus.iloc[index].topic}  ({focus.iloc[index].percent:.1f}%)",
    )
    selected = focus.iloc[choice]
    subject, topic = str(selected.subject), str(selected.topic)
    control_left, control_right = st.columns([1, 1], gap="large")
    with control_left:
        use_ai = st.toggle("Add newly generated AI questions", help="Requires ANTHROPIC_API_KEY in the environment.")
    with control_right:
        st.markdown(f'<div class="practice-context"><span>{escape(subject)}</span><strong>{escape(topic)}</strong><small>Recent average · {selected.percent:.1f}%</small></div>', unsafe_allow_html=True)

    base_key = f"practice_{sid}_{subject}_{topic}_{use_ai}"
    revision_key = f"{base_key}_revision"
    if revision_key not in st.session_state:
        st.session_state[revision_key] = 0
    if st.button("Refresh questions", icon="🔄"):
        st.session_state[revision_key] += 1

    key = f"{base_key}_{st.session_state[revision_key]}"
    if key not in st.session_state:
        questions = core.bank_questions(subject, topic, 5)
        if use_ai:
            try:
                generated = core.ai_questions(subject, topic, 5)
            except Exception as error:
                st.error(
                    f"AI question generation failed ({type(error).__name__}). "
                    "Built-in questions are available instead."
                )
            else:
                if generated is not None:
                    questions = pd.concat([questions, generated], ignore_index=True)
                else:
                    st.info("Set ANTHROPIC_API_KEY to enable AI-generated questions. Built-in questions are ready.")
        st.session_state[key] = questions.reset_index(drop=True)
        st.session_state[f"{key}_page"] = 0

    questions = st.session_state[key]
    if questions.empty:
        st.warning("There are no practice questions for this topic yet.")
        st.stop()

    questions_per_page = 5
    total_pages = (len(questions) + questions_per_page - 1) // questions_per_page
    page_key = f"{key}_page"
    current_page = min(st.session_state[page_key], total_pages - 1)
    st.session_state[page_key] = current_page
    first_question = current_page * questions_per_page
    last_question = min(first_question + questions_per_page, len(questions))
    result_key = f"{key}_result"
    st.caption(f"Page {current_page + 1} of {total_pages} · Questions {first_question + 1}–{last_question} of {len(questions)}")

    for index in range(first_question, last_question):
        question = questions.iloc[index]
        with st.container(border=True):
            st.markdown(f'<div class="question-label">QUESTION {index + 1:02}</div>', unsafe_allow_html=True)
            st.markdown(f"**{question.question}**")
            options = {"A": question.option_a, "B": question.option_b, "C": question.option_c, "D": question.option_d}
            st.radio(
                f"Answer {index + 1}", list(options),
                format_func=lambda option, values=options: f"{option}  {values[option]}",
                key=f"{key}_answer_{index}", index=None, label_visibility="collapsed",
                disabled=result_key in st.session_state,
            )

    navigation_left, navigation_right = st.columns(2)
    with navigation_left:
        if st.button("← Previous", disabled=current_page == 0, key=f"{key}_previous"):
            st.session_state[page_key] -= 1
            st.rerun()
    with navigation_right:
        if st.button("Next →", disabled=current_page == total_pages - 1, key=f"{key}_next"):
            st.session_state[page_key] += 1
            st.rerun()

    if st.button(
        "Submit quiz", type="primary", icon=":material/check:", key=f"{key}_submit",
        disabled=result_key in st.session_state,
    ):
        submitted_answers = {
            index: st.session_state.get(f"{key}_answer_{index}")
            for index in range(len(questions))
        }
        unanswered = [index + 1 for index, answer in submitted_answers.items() if answer is None]
        if unanswered:
            st.warning(
                f"Answer every question before submitting. Unanswered question(s): "
                f"{', '.join(map(str, unanswered))}."
            )
        else:
            correct = sum(
                submitted_answers[index] == question.correct_option
                for index, question in questions.iterrows()
            )
            core.save_practice_result(sid, subject, topic, correct, len(questions))
            st.session_state[result_key] = {
                "correct": correct,
                "answers": submitted_answers,
            }

    if result_key in st.session_state:
        result = st.session_state[result_key]
        st.success(
            f"Practice complete · {result['correct']} of {len(questions)} correct. "
            "Your progress report has been updated."
        )
        st.markdown("#### Answer review")
        for index, question in questions.iterrows():
            options = {"A": question.option_a, "B": question.option_b, "C": question.option_c, "D": question.option_d}
            correct_option = question.correct_option
            correct_answer = options[correct_option]
            chosen = result["answers"][index]
            if chosen == correct_option:
                st.markdown(f"**Question {index + 1}: Correct**")
            else:
                st.markdown(f"**Question {index + 1}: Review this one**")
                st.write(f"Your answer: {chosen} · {options[chosen]}")
            st.write(f"Correct answer: {correct_option} · {correct_answer}")
            explanation = question.get("explanation")
            if isinstance(explanation, str) and explanation.strip():
                st.caption(explanation)

elif page == "Placement Prep":
    if students.empty:
        st.warning("No learner data found. Load sample data or import a CSV to continue.")
        st.stop()

    sid = pick_student()
    page_header(
        "PLACEMENT STUDIO",
        "Mock interview practice",
        "Build confidence with realistic interview questions, thoughtful answer practice, and actionable coaching.",
    )
    st.markdown(
        '<div class="interview-hero"><span class="interview-hero-icon">✦</span>'
        '<div><strong>Practice out loud. Improve one answer at a time.</strong>'
        '<p>Your answers stay in this practice session. AI coaching is optional and only uses your selected role, '
        'the question, and the answer you submit.</p></div></div>',
        unsafe_allow_html=True,
    )

    session_key = f"placement_interview_{sid}"
    interview = st.session_state.get(session_key)
    if interview is None:
        st.markdown("#### Set up your interview")
        with st.form("placement_interview_setup", border=True):
            setup_left, setup_right = st.columns(2)
            with setup_left:
                role = st.selectbox("Target role", core.INTERVIEW_ROLES)
                interview_format = st.selectbox("Interview round", core.INTERVIEW_FORMATS)
            with setup_right:
                question_count = st.selectbox(
                    "Session length",
                    options=[3, 5],
                    format_func=lambda count: f"{count} questions · {'Quick round' if count == 3 else 'Full practice'}",
                )
                use_ai_coach = st.toggle(
                    "Use AI-generated questions and coaching",
                    help=(
                        "Requires ANTHROPIC_API_KEY. If enabled, the role and your submitted answers "
                        "are sent to Anthropic to generate questions and feedback."
                    ),
                )
            start_interview = st.form_submit_button("Start mock interview", type="primary")

        if start_interview:
            ai_enabled = use_ai_coach and core.ai_is_configured()
            generated_questions = None
            if use_ai_coach and not ai_enabled:
                st.info("ANTHROPIC_API_KEY is not configured. Starting with built-in questions and coaching guides.")
            elif ai_enabled:
                try:
                    generated_questions = core.ai_interview_questions(
                        role, interview_format, question_count
                    )
                except Exception as error:
                    st.error(
                        f"AI question generation failed ({type(error).__name__}). "
                        "Starting with built-in questions instead."
                    )
                if generated_questions is None:
                    st.info("AI questions are unavailable. Starting with built-in questions instead.")

            questions = generated_questions or core.interview_question_bank(
                role, interview_format, question_count
            )
            st.session_state[session_key] = {
                "id": uuid4().hex,
                "role": role,
                "format": interview_format,
                "questions": questions,
                "answers": [],
                "ratings": [],
                "feedback": [],
                "feedback_errors": [],
                "ai_coach": ai_enabled,
                "complete": False,
                "last_feedback_error": None,
            }
            st.rerun()
    elif interview["complete"]:
        st.success("Mock interview complete. Use the answer review to reflect and prepare your next attempt.")
        average_confidence = sum(interview["ratings"]) / len(interview["ratings"])
        summary_left, summary_middle, summary_right = st.columns(3)
        summary_left.metric("Questions practiced", len(interview["questions"]))
        summary_middle.metric("Average confidence", f"{average_confidence:.1f} / 5")
        summary_right.metric("Interview format", interview["format"])
        st.progress(average_confidence / 5)
        st.caption("Confidence is your own reflection, not a prediction of placement or hiring outcomes.")

        st.markdown("#### Your interview review")
        for index, question in enumerate(interview["questions"]):
            with st.expander(f"Question {index + 1} · {question['category']}"):
                st.markdown(f"**{question['question']}**")
                st.markdown("**Your answer**")
                st.write(interview["answers"][index])
                st.caption(f"Your confidence: {interview['ratings'][index]} / 5")
                st.markdown("**Suggested answer approach**")
                st.write(question["sample_answer"])
                st.caption(f"Listen for: {question['evaluation_criteria']}")
                feedback = interview["feedback"][index]
                if feedback:
                    st.markdown("**AI coach feedback**")
                    st.markdown(feedback)
                elif interview["feedback_errors"][index]:
                    st.warning(
                        "AI coaching could not be generated for this answer "
                        f"({interview['feedback_errors'][index]}). Use the suggested answer approach above."
                    )

        if st.button("Start another interview", type="primary", key=f"placement_restart_{interview['id']}"):
            del st.session_state[session_key]
            st.rerun()
    else:
        questions = interview["questions"]
        current_index = len(interview["answers"])
        total_questions = len(questions)
        st.markdown(
            f"**{escape(interview['role'])}** · {escape(interview['format'])} interview"
        )
        st.progress(current_index / total_questions)
        st.caption(f"Question {current_index + 1} of {total_questions} · {current_index} answered")
        if interview["last_feedback_error"]:
            st.warning(
                "Your answer was saved, but AI coaching could not be generated "
                f"({interview['last_feedback_error']}). You can still use the answer guide in your review."
            )

        question = questions[current_index]
        with st.container(border=True):
            st.markdown(
                f'<div class="question-label">{escape(question["category"].upper())} · QUESTION {current_index + 1:02}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(f"### {question['question']}")
            st.caption("Take a moment to structure your thoughts before you answer.")
            with st.form(f"placement_answer_{interview['id']}_{current_index}"):
                answer = st.text_area(
                    "Your answer",
                    placeholder="Type your answer here. For behavioral questions, try Situation → Task → Action → Result.",
                    height=180,
                    max_chars=4000,
                    label_visibility="collapsed",
                )
                confidence = st.slider(
                    "How confident are you in this answer?",
                    min_value=1,
                    max_value=5,
                    value=3,
                    help="This private self-rating is for your reflection; it does not affect your academic scores.",
                )
                submit_answer = st.form_submit_button(
                    "Finish interview" if current_index == total_questions - 1 else "Save answer & continue",
                    type="primary",
                )

        if submit_answer:
            if not answer.strip():
                st.warning("Write an answer before continuing.")
            else:
                feedback = None
                feedback_error = None
                if interview["ai_coach"]:
                    try:
                        feedback = core.ai_interview_feedback(
                            interview["role"],
                            question["question"],
                            answer,
                            question["evaluation_criteria"],
                        )
                    except Exception as error:
                        feedback_error = type(error).__name__
                interview["answers"].append(answer.strip())
                interview["ratings"].append(confidence)
                interview["feedback"].append(feedback)
                interview["feedback_errors"].append(feedback_error)
                interview["last_feedback_error"] = feedback_error
                if current_index == total_questions - 1:
                    interview["complete"] = True
                    history_key = f"placement_interview_history_{sid}"
                    history = st.session_state.get(history_key, [])
                    history.append(
                        {
                            "id": interview["id"],
                            "role": interview["role"],
                            "format": interview["format"],
                            "ratings": interview["ratings"].copy(),
                        }
                    )
                    st.session_state[history_key] = history
                st.session_state[session_key] = interview
                st.rerun()

        if st.button("End this interview", key=f"placement_end_{interview['id']}"):
            del st.session_state[session_key]
            st.rerun()

elif page == "Class overview":
    scores = core.all_scores()
    if scores.empty:
        st.warning("No learner data found. Load sample data or import a CSV to continue.")
        st.stop()

    groups = core.cluster_students(scores).merge(
        core.students_list()[["student_id", "class", "section", "branch"]],
        on="student_id",
        how="left",
    )
    topic_summary = core.topic_performance(scores)
    needs_support = groups[groups.group == "Needs Support"]
    page_header("FACULTY VIEW", "Class overview", "Spot shared learning gaps and see which learners may benefit from timely support.")

    metrics = st.columns(4)
    metrics[0].metric("Learners", f"{groups.student_id.nunique():,}")
    metrics[1].metric("Class average", f"{groups.overall.mean():.1f}%")
    metrics[2].metric("At risk", f"{len(needs_support):,}")
    metrics[3].metric("Topics tracked", f"{len(topic_summary):,}")

    chart_left, chart_right = st.columns(2, gap="large")
    counts = groups.group.value_counts().rename_axis("group").reset_index(name="students")
    with chart_left, st.container(border=True):
        st.markdown("#### Learner distribution")
        st.caption("Performance clusters based on subject averages")
        distribution = px.bar(
            counts, x="students", y="group", orientation="h", color="group", text="students",
            color_discrete_map=GROUP_COLORS,
        )
        distribution.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(polish_chart(distribution, 300), use_container_width=True, config={"displayModeBar": False})

    with chart_right, st.container(border=True):
        st.markdown("#### Most challenging topics")
        st.caption("Lowest class averages across all subjects")
        hardest = topic_summary.head(8).sort_values("percent", ascending=True)
        hard_fig = px.bar(hardest, x="percent", y="topic", orientation="h", color="subject", range_x=[0, 100])
        st.plotly_chart(polish_chart(hard_fig, 300), use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="section-heading"><div><span class="eyebrow">FOLLOW-UP</span><h2>Learner support list</h2></div></div>', unsafe_allow_html=True)
    filter_group, filter_class, filter_section, filter_branch, filter_search = st.columns([1.1, 0.9, 0.8, 1.2, 1.5])
    selected_group = filter_group.selectbox("Performance group", ["All groups", *sorted(groups.group.unique())])
    class_options = sorted(groups["class"].dropna().astype(str).loc[lambda values: values.str.strip() != ""].unique())
    section_options = sorted(groups.section.dropna().astype(str).loc[lambda values: values.str.strip() != ""].unique())
    branch_options = sorted(groups.branch.dropna().astype(str).loc[lambda values: values.str.strip() != ""].unique())
    selected_class = filter_class.selectbox("Class", ["All classes", *class_options])
    selected_section = filter_section.selectbox("Section", ["All sections", *section_options])
    selected_branch = filter_branch.selectbox("Branch", ["All branches", *branch_options])
    search = filter_search.text_input("Find a learner", placeholder="Name or ID")
    table = groups.copy()
    if selected_group != "All groups":
        table = table[table.group == selected_group]
    if selected_class != "All classes":
        table = table[table["class"] == selected_class]
    if selected_section != "All sections":
        table = table[table.section == selected_section]
    if selected_branch != "All branches":
        table = table[table.branch == selected_branch]
    if search:
        matches = pd.Series(False, index=table.index)
        for column in ["name", "student_id", "class", "section", "branch"]:
            matches |= table[column].fillna("").astype(str).str.contains(search, case=False, regex=False)
        table = table[matches]
    table = table[
        ["student_id", "name", "class", "section", "branch", "group", "overall"]
    ].sort_values("overall")
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "student_id": st.column_config.TextColumn("Student ID"),
            "class": st.column_config.TextColumn("Class"),
            "section": st.column_config.TextColumn("Section"),
            "branch": st.column_config.TextColumn("Branch"),
            "overall": st.column_config.NumberColumn("Overall", format="%.1f%%"),
        },
    )
