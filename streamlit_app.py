import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime, timedelta
import json
from google.oauth2 import service_account
import time

@st.cache_resource
def initialize_firebase():
    if not firebase_admin._apps:
        # Get the Firebase credentials JSON from Streamlit secrets
        key_dict = json.loads(st.secrets["textkey"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

# Initialize Firebase using Streamlit's caching
db = initialize_firebase()

def add_entry(title, content):
    doc_ref = db.collection("journal_entries").document()
    doc_ref.set({
        "title": title,
        "content": content,
        "timestamp": datetime.now()
    })

def get_entries():
    entries = db.collection("journal_entries").order_by("timestamp", direction=firestore.Query.DESCENDING).get()
    return entries

def update_entry(doc_id, title, content):
    doc_ref = db.collection("journal_entries").document(doc_id)
    doc_ref.update({
        "title": title,
        "content": content,
        "timestamp": datetime.now()
    })

def delete_entry(doc_id):
    db.collection("journal_entries").document(doc_id).delete()

st.title("My Journal App")

# Timer functionality
st.sidebar.header("Timer")
timer_duration = st.sidebar.number_input("Set Timer (minutes)", min_value=1, value=5)
start_timer = st.sidebar.button("Start Timer")

timer_placeholder = st.sidebar.empty()

if 'timer_end' not in st.session_state:
    st.session_state.timer_end = None

if start_timer:
    st.session_state.timer_end = datetime.now() + timedelta(minutes=timer_duration)

if st.session_state.timer_end:
    while datetime.now() < st.session_state.timer_end:
        time_left = st.session_state.timer_end - datetime.now()
        if time_left.total_seconds() > 0:
            mins, secs = divmod(time_left.seconds, 60)
            timer_placeholder.text(f"Time left: {mins:02d}:{secs:02d}")
            time.sleep(1)
            st.experimental_rerun()
        else:
            break
    
    timer_placeholder.text("Timer ended!")
    if st.sidebar.button("Reset Timer"):
        st.session_state.timer_end = None
        st.experimental_rerun()

# Sidebar for adding new entries
st.sidebar.header("Add New Entry")
new_title = st.sidebar.text_input("Title")
new_content = st.sidebar.text_area("Content")
if st.sidebar.button("Add Entry"):
    add_entry(new_title, new_content)
    st.sidebar.success("Entry added successfully!")

# Main area for displaying and managing entries
entries = get_entries()
for entry in entries:
    data = entry.to_dict()
    with st.expander(f"{data['title']} - {data['timestamp'].strftime('%Y-%m-%d %H:%M')}"):
        st.write(data['content'])
        
        # Update functionality
        update_title = st.text_input("Update Title", value=data['title'], key=f"update_title_{entry.id}")
        update_content = st.text_area("Update Content", value=data['content'], key=f"update_content_{entry.id}")
        if st.button("Update Entry", key=f"update_button_{entry.id}"):
            update_entry(entry.id, update_title, update_content)
            st.success("Entry updated successfully!")
            st.experimental_rerun()
        
        # Delete functionality
        if st.button("Delete Entry", key=f"delete_button_{entry.id}"):
            delete_entry(entry.id)
            st.success("Entry deleted successfully!")
            st.experimental_rerun()