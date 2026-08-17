import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# -----------------------------------------------------------------------------
# 1. INITIALIZATION & LAYOUT CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Kids Music Team", layout="centered")
st.title("Kids Music Team Portal")

# Connect to Google Sheets via Streamlit Secrets Configuration
conn = st.connection("gsheets", type=GSheetsConnection)

# Define choice menus for the registration layer
service_list = ["10AM", "12NN", "2PM", "4PM", "6PM"]
week_list = ["Week1", "Week2", "Week3", "Week4", "Week5"]
role_list = ["AG", "WL"]
month_list = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

# Initialize tracking states to maintain active browser session memory
if "search_clicked" not in st.session_state:
    st.session_state.search_clicked = False
if "searched_name" not in st.session_state:
    st.session_state.searched_name = ""

# -----------------------------------------------------------------------------
# STEP 1: USER IDENTITY LOOKUP SEARCH BAR
# -----------------------------------------------------------------------------
search_input = st.text_input("Welcome to Kids Church! Search your name!", value=st.session_state.searched_name).strip()

if st.button("Name lookup", type="secondary"):
    if not search_input:
        st.warning("Please enter a name to search.")
        st.session_state.search_clicked = False
    else:
        st.session_state.search_clicked = True
        st.session_state.searched_name = search_input

# -----------------------------------------------------------------------------
# STEP 2: ACTIVE SESSION CONTAINER (Runs once a valid search is performed)
# -----------------------------------------------------------------------------
if st.session_state.search_clicked:
    current_name = st.session_state.searched_name
    st.write("---")

    # 1. Fetch live production sheet data from the cloud
    try:
        # Clear cache to guarantee real-time updates are evaluated
        df = conn.read(ttl="0d")
    except Exception:
        st.error("Failed to connect to Google Sheets. Verify your link configurations.")
        st.stop()

    required_columns = ["FNM", "SRV", "WK", "Role", "Month"]

    # Ensure standard structural schema columns are valid
    if not all(col in df.columns for col in required_columns):
        st.error("Google Sheet headers are missing structural column fields (FNM, SRV, WK, Role, Month).")
        st.stop()

    # Filter rows matching the lowercase searched name parameter
    match_indices = df["FNM"].fillna("").astype(str).str.strip().str.lower() == current_name.lower()
    existing_entries = df[match_indices]

    # Evaluate profile footprint scenario
    has_profile = not existing_entries.empty

    if has_profile:
        st.success(f"Welcome back, **{current_name}**! Here are your active serving schedules:")

        # Format display grid view metrics for the end-user
        display_df = existing_entries[required_columns].copy()
        display_df.columns = ["Name", "Service Time", "Serving Week", "Role Assignment", "Month Scheduled"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.info("If you have more time available, you can fill out the this form again :) .")
    else:
        st.warning(f"I cannot find any registered for you '**{current_name}**'. You can fill out the form below:")

    # -----------------------------------------------------------------------------
    # STEP 3 & 4: MULTI-PURPOSE SCHEDULING FORM
    # -----------------------------------------------------------------------------
    with st.form("registration_form", clear_on_submit=True):
        st.subheader("Serving Schedules")

        # User input fields
        srv_term = st.selectbox("Select Service Time:", options=service_list)
        wk_term = st.selectbox("Select Serving Week:", options=week_list)
        rl_term = st.selectbox("Select Role:", options=role_list)
        mnt_term = st.selectbox("Select Month:", options=month_list)

        # Context-aware submit button text assignment
        button_label = "Register for Kids Music" if has_profile else "Create New Entry"
        submit_shift = st.form_submit_button(button_label, type="primary")

        if submit_shift:
            # Re-read cloud data frame at execution timestamp to intercept cross-traffic collision entries
            df_latest = conn.read(ttl="0d")

            # Exact combination collision block analysis loop
            m_name = df_latest["FNM"].fillna("").astype(str).str.strip().str.lower() == current_name.lower()
            m_srv = df_latest["SRV"].fillna("").astype(str).str.strip().str.lower() == srv_term.lower()
            m_wk = df_latest["WK"].fillna("").astype(str).str.strip().str.lower() == wk_term.lower()
            m_role = df_latest["Role"].fillna("").astype(str).str.strip().str.lower() == rl_term.lower()
            m_mnt = df_latest["Month"].fillna("").astype(str).str.strip().str.lower() == mnt_term.lower()

            duplicate_collision = (m_name & m_srv & m_wk & m_role & m_mnt).any()

            if duplicate_collision:
                st.error(
                    f"Duplicate Error: You are already serving for the {srv_term} on {wk_term} as a/an {rl_term} in {mnt_term}!")
            else:
                # Structure dictionary row data mapping parameters
                new_row = pd.DataFrame([{
                    "FNM": current_name,
                    "SRV": srv_term,
                    "WK": wk_term,
                    "Role": rl_term,
                    "Month": mnt_term
                }])

                # Append payload dataframe directly targeting target cloud worksheet node indexes
                df_updated = pd.concat([df_latest, new_row], ignore_index=True)

                try:
                    conn.update(data=df_updated)
                    st.toast("Thank you for serving with us! Our records have been updated!", icon="🚀")
                    st.success(
                        f"Success! Registered {current_name} for {wk_term} ({srv_term}) as {rl_term} for {mnt_term}.")

                    # Force runtime container interface reset to reload components live
                    st.rerun()
                except Exception as e:
                    st.error(f"Network write error occurred: {e}")
