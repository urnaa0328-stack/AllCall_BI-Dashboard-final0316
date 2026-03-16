import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta, date


def _norm_str(x) -> str:
    return "" if pd.isna(x) else str(x).strip()


def _parse_num(x):
    if pd.isna(x):
        return 0.0
    s = str(x).strip().replace(",", "")
    try:
        return float(s)
    except Exception:
        return 0.0


def _prepare_operation_df(df: pd.DataFrame):

    dfx = df.copy()

    rename_map = {
        "Ажлын төрөл": "task_type",
        "Төслийн нэр": "project_name",
        "Эхлэх огноо": "start_date",
        "Дуусах огноо": "end_date",
        "Хугацаа": "duration_days",
        "Хариуцагч": "owner",
        "Дэмжигч": "supporter",
        "Явцын тайлбар": "progress_note",
        "Явц": "status",
    }

    dfx = dfx.rename(columns=rename_map)

    for col in ["task_type","project_name","owner","supporter","progress_note","status"]:
        if col in dfx.columns:
            dfx[col] = dfx[col].apply(_norm_str)

    for col in ["start_date","end_date"]:
        if col in dfx.columns:
            dfx[col] = pd.to_datetime(dfx[col], errors="coerce")

    if "duration_days" in dfx.columns:
        dfx["duration_days_num"] = dfx["duration_days"].apply(_parse_num)
    else:
        dfx["duration_days_num"] = 0.0

    return dfx


def _filter_period(df: pd.DataFrame, dfrom: date, dto: date):

    if "start_date" not in df.columns:
        return df.copy()

    start_dt = datetime.combine(dfrom, datetime.min.time())
    end_dt = datetime.combine(dto + timedelta(days=1), datetime.min.time())

    return df[(df["start_date"] >= start_dt) & (df["start_date"] < end_dt)].copy()


def render_operation_dashboard(df: pd.DataFrame, dfrom: date, dto: date, accent: str):

    st.subheader("🛠 Operation Dashboard")

    dfx = _prepare_operation_df(df)
    cur = _filter_period(dfx, dfrom, dto)

    today = datetime.today().date()

    total_tasks = len(cur)

    done_count = int((cur["status"] == "Хийгдсэн").sum())
    in_progress_count = int((cur["status"] == "Хийгдэж байна").sum())
    waiting_count = int((cur["status"] == "Хүлээгдэж байна").sum())

    completion_rate = (done_count / total_tasks * 100) if total_tasks else 0

    avg_duration = float(cur["duration_days_num"].mean()) if total_tasks else 0


    # -------------------------
    # MONTH RANGE
    # -------------------------

    month_start = today.replace(day=1)

    if today.month == 12:
        month_end = today.replace(year=today.year+1,month=1,day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month+1,day=1) - timedelta(days=1)


    # -------------------------
    # MONTH TASKS
    # -------------------------

    month_tasks = cur[
        (cur["status"] != "Хийгдсэн") &
        (cur["end_date"].notna()) &
        (cur["end_date"].dt.date >= month_start) &
        (cur["end_date"].dt.date <= month_end)
    ].copy()


    # -------------------------
    # OWNER WORKLOAD (MONTH)
    # -------------------------

    owner_month_df = pd.DataFrame(columns=["owner","count"])

    if "owner" in month_tasks.columns:

        vc = month_tasks["owner"].replace("",pd.NA).dropna().value_counts()

        if not vc.empty:
            owner_month_df = vc.reset_index()
            owner_month_df.columns = ["owner","count"]


    # -------------------------
    # OVERDUE TASKS
    # -------------------------

    overdue_tasks = cur[
        (cur["status"] != "Хийгдсэн") &
        (cur["end_date"].notna()) &
        (cur["end_date"].dt.date < today)
    ]


    # -------------------------
    # TASK TYPE
    # -------------------------

    task_type_df = pd.DataFrame(columns=["task_type","count"])

    vc = cur["task_type"].replace("",pd.NA).dropna().value_counts()

    if not vc.empty:
        task_type_df = vc.head(10).reset_index()
        task_type_df.columns = ["task_type","count"]


    # -------------------------
    # OWNER WORKLOAD
    # -------------------------

    owner_df = pd.DataFrame(columns=["owner","count"])

    vc = cur["owner"].replace("",pd.NA).dropna().value_counts()

    if not vc.empty:
        owner_df = vc.head(10).reset_index()
        owner_df.columns = ["owner","count"]


    # -------------------------
    # STATUS
    # -------------------------

    status_df = cur["status"].replace("",pd.NA).dropna().value_counts().reset_index()
    status_df.columns = ["status","count"]


    # -------------------------
    # KPI
    # -------------------------

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Нийт ажил", total_tasks)
    c2.metric("Хийгдсэн", done_count)
    c3.metric("Хийгдэж байна", in_progress_count)
    c4.metric("Хүлээгдэж байна", waiting_count)

    c5,c6,c7,c8 = st.columns(4)

    c5.metric("Гүйцэтгэлийн хувь", f"{completion_rate:.1f}%")
    c6.metric("Энэ сард дуусах ажил", len(month_tasks))
    c7.metric("Хоцорсон ажил", len(overdue_tasks))
    c8.metric("Дундаж хугацаа", f"{avg_duration:.1f} хоног")

    st.divider()


    # -------------------------
    # CHARTS
    # -------------------------

    left,right = st.columns(2)

    with left:

        st.markdown("#### 📂 Ажлын төрлийн хуваарилалт")

        chart = alt.Chart(task_type_df).mark_bar(
            color=accent
        ).encode(
            y=alt.Y("task_type:N",sort="-x"),
            x="count:Q",
            tooltip=["task_type","count"]
        )

        st.altair_chart(chart,use_container_width=True)


    with right:

        st.markdown("#### 👤 Хариуцагчийн workload")

        chart = alt.Chart(owner_df).mark_bar(
            color="#56B4FF"
        ).encode(
            y=alt.Y("owner:N",sort="-x"),
            x="count:Q",
            tooltip=["owner","count"]
        )

        st.altair_chart(chart,use_container_width=True)


    st.divider()

    left2,right2 = st.columns(2)

    with left2:

        st.markdown("#### 📊 Явцын төлөв")

        chart = alt.Chart(status_df).mark_arc(innerRadius=60).encode(
            theta="count",
            color="status",
            tooltip=["status","count"]
        )

        st.altair_chart(chart,use_container_width=True)


    with right2:

        st.markdown("#### 👤 Энэ сард дуусгах ажил (хариуцагчаар)")

        if owner_month_df.empty:
            st.info("Энэ сард дуусах ажил алга")
        else:

            chart = alt.Chart(owner_month_df).mark_bar(
                color=accent
            ).encode(
                y=alt.Y("owner:N",sort="-x"),
                x="count:Q",
                tooltip=["owner","count"]
            )

            st.altair_chart(chart,use_container_width=True)


    st.divider()


    # -------------------------
    # OVERDUE LIST
    # -------------------------

    st.markdown("### ⚠️ Хоцорсон ажил")

    if overdue_tasks.empty:
        st.success("Хоцорсон ажил байхгүй")
    else:
        st.dataframe(overdue_tasks,use_container_width=True)


    # -------------------------
    # MONTH TASK LIST
    # -------------------------

    st.markdown("### 🔥 Энэ сард дуусах ажил")

    if month_tasks.empty:
        st.info("Энэ сард дуусах ажил алга")
    else:
        st.dataframe(month_tasks,use_container_width=True)


    st.divider()

    st.markdown("### 📋 Бүх ажил")

    st.dataframe(cur,use_container_width=True)

    csv = cur.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "⬇️ CSV татах",
        csv,
        "operation_dashboard.csv",
        "text/csv"
    )