import base64
import os
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

st.set_page_config(page_title="Kids Church", layout="centered")
st.title("Kids Church Registration Portal")

st.html("""
    <style>
        /* 1. Main Background Color */
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: #A9D9E8 !important;
        }

/* 2. Sidebar and Input Widgets Background Color */
[data-testid="stSidebar"], [data-testid="stBaseButton-secondary"] {
    background-color: #FDE3E6 !important;
    color: #000000 !important;
}

        /* 4. Primary Accent Elements (Buttons) */
        [data-testid="stBaseButton-primary"], button {
            background-color: #FFDB58 !important;
            color: #31333F !important;
            border: none !important;
        }



    </style>
""")

current_calendar_month = datetime.now().strftime("%B")
current_calendar_year = datetime.now().strftime("%Y")

IMAGE_FILE2 = "kds.png"

if os.path.exists(IMAGE_FILE2):
    st.sidebar.image(
        IMAGE_FILE2,
        use_container_width=True,

    )
else:
    st.sidebar.warning(f"Sidebar image '{IMAGE_FILE2}' not found.")

st.sidebar.write("---")

st.sidebar.subheader("This week's songs:")

st.sidebar.markdown("[Slow song - Ruler of Nations](https://www.youtube.com/watch?v=Jfg7_1TRDDQ)")
st.sidebar.markdown("[Fast song - Tribes](https://www.youtube.com/watch?v=66H4mLGgZ54)")

st.sidebar.write("---")

st.sidebar.subheader("This month's series grid:")
IMAGE_FILE = "series.jpg"

if os.path.exists(IMAGE_FILE):
    st.sidebar.image(
        IMAGE_FILE,
        use_container_width=True,

    )
else:
    st.sidebar.warning(f"Sidebar image '{IMAGE_FILE}' not found.")

conn = st.connection("gsheets", type=GSheetsConnection)


def run_kds_music():
    service_list = ["10AM", "12NN", "2PM", "4PM", "6PM"]
    week_list = ["Week1", "Week2", "Week3", "Week4", "Week5"]
    role_list = ["AG", "WL"]
    month_list = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    if "search_clicked" not in st.session_state:
        st.session_state.search_clicked = False
    if "searched_name" not in st.session_state:
        st.session_state.searched_name = ""

    search_input = st.text_input(
        "Would you like to serve as a worship leader or play the guitar? Please search your name:",
        value=st.session_state.searched_name).strip()

    if st.button("Music lookup", type="secondary", key="music_lookup_button"):
        if not search_input:
            st.warning("Please enter a name to search.")
            st.session_state.search_clicked = False
        else:
            st.session_state.search_clicked = True
            st.session_state.searched_name = search_input

            st.rerun()

    if st.session_state.search_clicked:
        current_name = st.session_state.searched_name
        st.write("---")

        # 1. Fetch live production sheet data from the cloud
        try:
            df = conn.read(ttl="0d")
        except Exception:
            st.error("Failed to connect to Google Sheets. Verify your link configurations.")
            st.stop()

        required_columns = ["FNM", "SRV", "WK", "Role", "Month"]

        if not all(col in df.columns for col in required_columns):
            st.error("Google Sheet headers are missing structural column fields (FNM, SRV, WK, Role, Month).")
            st.stop()

        match_indices = df["FNM"].fillna("").astype(str).str.strip().str.lower() == current_name.lower()
        existing_entries = df[match_indices]

        has_profile = not existing_entries.empty

        if has_profile:
            st.success(f"Welcome back, **{current_name}**! Here are your active serving schedules:")

            display_df = existing_entries[required_columns].copy()
            display_df.columns = ["Name", "Service Time", "Serving Week", "Role Assignment", "Month Scheduled"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            st.info("If you have more time available, you can fill out the this form again :) .")
            st.info(
                "Note: If you wish to change the schedule you have, please create a new entry and reach out to the admin :)")
        else:
            st.warning(
                f"I cannot find any registered services for you, **{current_name}**. You can fill out the form below:")

        with st.form("registration_form", clear_on_submit=True):
            st.subheader("Serving Schedules")

            srv_term = st.selectbox("Select Service Time:", options=service_list)
            wk_term = st.selectbox("Select Serving Week:", options=week_list)
            rl_term = st.selectbox("Select Role:", options=role_list)
            mnt_term = st.selectbox("Select Month:", options=month_list)

            button_label = "Register for Kids Music" if has_profile else "Create New Entry"
            submit_shift = st.form_submit_button(button_label, type="primary")

            if submit_shift:
                df_latest = conn.read(ttl="0d")

                m_name = df_latest["FNM"].fillna("").astype(str).str.strip().str.lower() == current_name.lower()
                m_srv = df_latest["SRV"].fillna("").astype(str).str.strip().str.lower() == srv_term.lower()
                m_wk = df_latest["WK"].fillna("").astype(str).str.strip().str.lower() == wk_term.lower()
                m_role = df_latest["Role"].fillna("").astype(str).str.strip().str.lower() == rl_term.lower()
                m_mnt = df_latest["Month"].fillna("").astype(str).str.strip().str.lower() == mnt_term.lower()

                duplicate_collision = (m_name & m_srv & m_wk & m_role & m_mnt).any()
                matching_slots = df_latest[m_srv & m_wk & m_role & m_mnt]
                duplicate_service = (m_srv & m_wk & m_role & m_mnt).any()

                if duplicate_collision:
                    st.error(
                        f"Duplicate Error: You are already serving for the {srv_term} on {wk_term} as a/an {rl_term} in {mnt_term}!")

                elif duplicate_service:
                    st.error(
                        f"Oops, someone is already serving for the {srv_term} on {wk_term} as a/an {rl_term} in {mnt_term}!")
                    conflicting_row = matching_slots[required_columns].copy()
                    conflicting_row.columns = ["Name", "Service Time", "Serving Week", "Role Assignment",
                                               "Month Scheduled"]
                    st.dataframe(conflicting_row, use_container_width=True, hide_index=True)

                else:
                    new_row = pd.DataFrame([{
                        "FNM": current_name,
                        "SRV": srv_term,
                        "WK": wk_term,
                        "Role": rl_term,
                        "Month": mnt_term,
                        "YR": str(2026),
                        "Agegroup": "Primary"
                    }])
                    df_updated = pd.concat([df_latest, new_row], ignore_index=True)

                    try:
                        conn.update(data=df_updated)
                        st.toast("Thank you for serving with us! Our records have been updated!", icon="🚀")
                        st.success(
                            f"Success! Registered {current_name} for {wk_term} ({srv_term}) as {rl_term} for {mnt_term}.")

                        st.rerun()
                    except Exception as e:
                        st.error(f"Network write error occurred: {e}")


def run_kds_teacher():
    service_list2 = ["10AM", "12NN", "2PM", "4PM", "6PM"]
    week_list2 = ["Week1", "Week2", "Week3", "Week4", "Week5"]
    role_list2 = ["Volunteer", "Preacher"]
    month_list2 = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    age_list2 = ["Preschool1", "Preschool2", "Primary", "Preteens"]

    if "search_clicked2" not in st.session_state:
        st.session_state.search_clicked2 = False
    if "searched_name2" not in st.session_state:
        st.session_state.searched_name2 = ""

    search_input2 = st.text_input("Would you like to volunteer or teach kids? Please search your name:",
                                  value=st.session_state.searched_name2,
                                  key="kds_teacher_search_input")

    if st.button("Teacher lookup", type="secondary", key="teacher_lookup_button"):
        if not search_input2:
            st.warning("Please enter a name to search.")
            st.session_state.search_clicked2 = False
        else:
            st.session_state.search_clicked2 = True
            st.session_state.searched_name2 = search_input2

            st.rerun()

    if st.session_state.search_clicked2:
        current_name2 = st.session_state.searched_name2
        st.write("---")

        # 1. Fetch live production sheet data from the cloud
        try:
            df = conn.read(ttl="0d")
        except Exception:
            st.error("Failed to connect to Google Sheets. Verify your link configurations.")
            st.stop()

        required_columns2 = ["FNM", "SRV", "WK", "Role", "Month", "Agegroup"]

        if not all(col in df.columns for col in required_columns2):
            st.error("Google Sheet headers are missing structural column fields (FNM, SRV, WK, Role, Month, Agegroup).")
            st.stop()

        match_indices2 = df["FNM"].fillna("").astype(str).str.strip().str.lower() == current_name2.lower()
        existing_entries2 = df[match_indices2]

        has_profile2 = not existing_entries2.empty

        if has_profile2:
            st.success(f"Welcome back, **{current_name2}**! Here are your active serving schedules:")

            display_df2 = existing_entries2[required_columns2].copy()
            display_df2.columns = ["Name", "Service Time", "Serving Week", "Role Assignment", "Month Scheduled",
                                   "Age Group"]
            st.dataframe(display_df2, use_container_width=True, hide_index=True)

            st.info("If you have more time available, you can fill out the this form again :) .")
            st.info(
                "Note: If you wish to change the schedule you have, please create a new entry and reach out to the admin :)")
        else:
            st.warning(
                f"I cannot find any registered services for you, **{current_name2}**. You can fill out the form below:")

        with st.form("registration_form2", clear_on_submit=True):
            st.subheader("Serving Schedules")

            srv_term2 = st.selectbox("Select Service Time:", options=service_list2)
            wk_term2 = st.selectbox("Select Serving Week:", options=week_list2)
            rl_term2 = st.selectbox("Select Role:", options=role_list2)
            mnt_term2 = st.selectbox("Select Month:", options=month_list2)
            age_term2 = st.selectbox("Select Age Group:", options=age_list2)

            button_label2 = "Register as a Kids Teacher" if has_profile2 else "Create New Entry"
            submit_shift2 = st.form_submit_button(button_label2, type="primary")

            if submit_shift2:
                df_latest2 = conn.read(ttl="0d")

                m_name2 = df_latest2["FNM"].fillna("").astype(str).str.strip().str.lower() == current_name2.lower()
                m_srv2 = df_latest2["SRV"].fillna("").astype(str).str.strip().str.lower() == srv_term2.lower()
                m_wk2 = df_latest2["WK"].fillna("").astype(str).str.strip().str.lower() == wk_term2.lower()
                m_role2 = df_latest2["Role"].fillna("").astype(str).str.strip().str.lower() == rl_term2.lower()
                m_mnt2 = df_latest2["Month"].fillna("").astype(str).str.strip().str.lower() == mnt_term2.lower()
                m_age2 = df_latest2["Agegroup"].fillna("").astype(str).str.strip().str.lower() == age_term2.lower()

                duplicate_collision2 = (m_name2 & m_srv2 & m_wk2 & m_role2 & m_mnt2 & m_age2).any()
                matching_slots2 = df_latest2[m_srv2 & m_wk2 & m_role2 & m_mnt2]
                duplicate_service2 = (m_srv2 & m_wk2 & m_role2 & m_mnt2).any()

                if duplicate_collision2:
                    st.error(
                        f"Duplicate Error: You are already serving for the {srv_term2} on {wk_term2} as a/an {rl_term2} in {mnt_term2}!")

                elif duplicate_service2:
                    st.error(
                        f"Oops, someone is already serving for the {srv_term2} on {wk_term2} as a/an {rl_term2} in {mnt_term2} for {age_term2}!")
                    conflicting_row2 = matching_slots2[required_columns2].copy()
                    conflicting_row2.columns = ["Name", "Service Time", "Serving Week", "Role Assignment",
                                                "Month Scheduled", "Agegroup"]
                    st.dataframe(conflicting_row2, use_container_width=True, hide_index=True)

                else:
                    new_row = pd.DataFrame([{
                        "FNM": current_name2,
                        "SRV": srv_term2,
                        "WK": wk_term2,
                        "Role": rl_term2,
                        "Month": mnt_term2,
                        "YR": str(2026),
                        "Agegroup": age_term2
                    }])
                    df_updated2 = pd.concat([df_latest2, new_row], ignore_index=True)

                    try:
                        conn.update(data=df_updated2)
                        st.toast("Thank you for serving with us! Our records have been updated!", icon="🚀")
                        st.success(
                            f"Success! Registered {current_name2} for {wk_term2} ({srv_term2}) as {rl_term2} in {mnt_term2} for {age_term2}.")

                        st.rerun()
                    except Exception as e:
                        st.error(f"Network write error occurred: {e}")


## Sidebar
## Weekly list

st.sidebar.write("---")
st.sidebar.subheader("📋 Weekly Roster Finder")


@st.dialog("This Week's Volunteers")
def show_weekly_volunteers():
    st.write("We thank the Lord for your hearts to serve!")

    week_list3 = ["Week1", "Week2", "Week3", "Week4", "Week5"]

    try:
        df_week = conn.read(ttl="0d")
    except Exception:
        st.error("Could not fetch the sheet database.")
        return
    target_week = st.selectbox("Select Week to View:", options=week_list3, key="dialog_view_week_select")

    match_wk = df_week["WK"].fillna("").astype(str).str.strip().str.lower() == target_week.lower()
    match_mnt = df_week["Month"].fillna("").astype(str).str.strip().str.lower() == current_calendar_month.lower()

    weekly_df = df_week[match_wk & match_mnt]

    if weekly_df.empty:
        st.info(f"No volunteers are registered to serve on **{target_week}** yet.")
    else:
        weekly_df = weekly_df[["FNM", "SRV", "Role", "Month", "Agegroup"]]
        weekly_df.columns = ["Name", "Service Time", "Role Assignment", "Month", "Age Group"]

        weekly_df = weekly_df.sort_values(by="Service Time")

        st.success(f"Found **{len(weekly_df)}** team member(s) serving in {target_week}:")
        st.dataframe(weekly_df, use_container_width=True, hide_index=True)


if st.sidebar.button("Check Weekly Roster 🔍", use_container_width=True):
    show_weekly_volunteers()

## Monthly list

st.sidebar.write("---")
st.sidebar.subheader("📋 Monthly Roster Finder")


@st.dialog("This Month's Volunteers")
def show_monthly_volunteers():
    st.write(f"We thank the Lord for your hearts to serve!")

    try:
        # FIX: Ensure you are reading the data into a variable named df_week
        # (or change df_week below to match whatever variable you use here)
        df_week = conn.read(ttl="0d")
    except Exception:
        st.error("Could not fetch the sheet database.")
        return

    match_mnt = df_week["Month"].fillna("").astype(str).str.strip().str.lower() == current_calendar_month.lower()

    monthly_df = df_week[match_mnt]

    if monthly_df.empty:
        st.info(f"No volunteers are registered for **{current_calendar_month}** yet.")
    else:
        monthly_df = monthly_df[["FNM", "SRV", "WK", "Role", "Month", "Agegroup"]]
        monthly_df.columns = ["Name", "Service Time", "Serving Week", "Role Assignment", "Month", "Agegroup"]
        monthly_df = monthly_df.sort_values(by=["Serving Week", "Service Time", "Month", "Agegroup"])

        st.success(f"Found **{len(monthly_df)}** total team member(s) serving this month:")
        st.dataframe(monthly_df, use_container_width=True, hide_index=True)


if st.sidebar.button("Check Monthly Roster 🔍", use_container_width=True):
    show_monthly_volunteers()

st.sidebar.write("---")
st.sidebar.subheader("📋 Yearly Roster Finder")


@st.dialog("This Year's Volunteers")
def show_yearly_volunteers():
    st.write(f"We thank the Lord for your hearts to serve!")

    try:
        yearly_df = conn.read(ttl="0d")
    except Exception:
        st.error("Could not fetch the sheet database.")
        return

    if yearly_df.empty:
        st.info("No volunteers are registered in the database yet.")
    else:
        yearly_df = yearly_df[["FNM", "SRV", "WK", "Role", "Month", "YR"]]

        yearly_df.columns = ["Name", "Service Time", "Serving Week", "Role Assignment", "Month", "Year"]
        yearly_df = yearly_df.sort_values(by=["Serving Week", "Service Time", "Month", "Year"])

        st.success(f"Here is a report of all who have served and will serve throughout the year:")
        st.dataframe(yearly_df, use_container_width=True, hide_index=True)


if st.sidebar.button("Check Yearly Roster 🔍", use_container_width=True):
    show_yearly_volunteers()

## TABS

tab1, tab2, tab3 = st.tabs(["🎵 Kids Music Team", "📖 Kids Teachers Team", "👤 Kids Coodinators"])

with tab1:
    run_kds_music()

with tab2:
    run_kds_teacher()

with tab3:
    st.write("If you have any questions or concerns, you can reach out to the following coordinators: ")

    image_filename = "428153935_7645976362101063_1868470333701431125_n.jpg"

    try:
        # 2. Read the local file and convert it into a string
        with open(image_filename, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        img_src = f"data:image/jpeg;base64,{encoded_string}"
    except FileNotFoundError:
        # If the file path is wrong, it shows a placeholder so your app doesn't crash
        img_src = "https://unsplash.com"
        st.error(f"Could not find the image file: {image_filename}")

    # 3. Inject the data string directly into the HTML source
    st.html(
        f"""
        <div style="
            border: 2px solid #4A90E2;
            border-radius: 10px;
            padding: 15px;
            width: 180px;
            text-align: center;
            background-color: #f9f9f9;
            font-family: sans-serif;
        ">
            <img src="{img_src}" 
                 style="width: 100%; border-radius: 5%; margin-bottom: 10px; object-fit: cover;">

            <h3 style="margin: 0 0 5px 0; color: #333; font-size: 18px; font-weight: bold;">
                John Venn
            </h3>
            <p style="margin: 0; color: #666; font-size: 13px; line-height: 1.3;">
                12 Noon - Worship Service Leader
            </p>
        </div>
        """
    )

