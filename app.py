from html import escape
from pathlib import Path

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
page_names = ["Student dashboard", "Practice", "Class overview", "Upload data"]
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
