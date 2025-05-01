import streamlit as st
import requests
import json
import re  # <-- for password validation

st.title("Clinical Note Processor with Patient Registration")

# --- Patient Registration Form ---
st.header("Enter Patient / User Details")

with st.form("user_form"):
    first_name = st.text_input("First Name*", max_chars=50)
    last_name = st.text_input("Last Name*", max_chars=50)
    birth_date = st.date_input("Birth Date*")
    gender = st.selectbox("Gender*", options=["male", "female", "other"])
    email = st.text_input("Email*", max_chars=100)
    password = st.text_input("Password*", type="password")
    username = st.text_input("Username*", max_chars=50)
    phone = st.text_input("Phone", max_chars=20)
    address = st.text_area("Address", max_chars=200)

    preferred_alert_mode = st.selectbox(
        "Preferred Alert Mode*", options=["email", "call", "text"]
    )

    secondary_options = [mode for mode in ["email", "call", "text"] if mode != preferred_alert_mode]

    secondary_alert_mode = st.selectbox(
        "Secondary Alert Mode* (must choose one of the other two)",
        options=secondary_options
    )

    pdf_file = st.file_uploader("Upload Clinical Note (PDF)*", type=["pdf"])

    submit_button = st.form_submit_button("Submit and Process")

# --- Password Validation Function ---
def is_valid_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True

# --- Form Submission Action ---
if submit_button:
    if not first_name:
        st.error("First Name is required.")
    elif not last_name:
        st.error("Last Name is required.")
    elif not email:
        st.error("Email is required.")
    elif not password:
        st.error("Password is required.")
    elif not is_valid_password(password):
        st.error("Password must be at least 8 characters long and include at least one special character (!@#$%^&* etc).")
    elif not username:
        st.error("Username is required.")
    elif not preferred_alert_mode:
        st.error("Preferred Alert Mode is required.")
    elif not secondary_alert_mode:
        st.error("Secondary Alert Mode is required.")
    elif not pdf_file:
        st.error("PDF Upload is required.")
    else:
        with st.spinner('Processing clinical note...'):
            # Prepare user metadata
            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "birth_date": birth_date.strftime("%Y-%m-%d"),
                "gender": gender,
                "email": email,
                "password": password,
                "username": username,
                "phone": phone,
                "address": address,
                "preferred_alert_mode": preferred_alert_mode,
                "secondary_alert_mode": secondary_alert_mode
            }

            # Send PDF + user metadata to backend
            files = {"pdf": pdf_file}
            payload = {"user_data": json.dumps(user_data)}
            response = requests.post("http://localhost:4040/process_note", files=files, data=payload)

            if response.status_code == 200:
                st.success("Processing Complete!")
                #st.json(response.json())
                if response.json()['registration']["status"] == 200:
                    st.success("Registration Complete!")
            else:
                st.error(f"Error {response.status_code}: {response.text}")
