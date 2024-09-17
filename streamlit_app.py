import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from openai import OpenAI

@st.cache_resource
def initialize_firebase():
    if not firebase_admin._apps:
        key_dict = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

# Initialize Firebase using Streamlit's caching
db = initialize_firebase()

# Set up OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def get_encryption_key(password):
    password = password.encode()
    salt = b'salt_'  # In a real app, use a secure random salt and store it
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key

def encrypt_text(text, password):
    key = get_encryption_key(password)
    f = Fernet(key)
    return f.encrypt(text.encode()).decode()

def decrypt_text(encrypted_text, password):
    key = get_encryption_key(password)
    f = Fernet(key)
    return f.decrypt(encrypted_text.encode()).decode()

def add_entry(title, content, password):
    encrypted_title = encrypt_text(title, password)
    encrypted_content = encrypt_text(content, password)
    doc_ref = db.collection("journal_entries").document()
    doc_ref.set({
        "title": encrypted_title,
        "content": encrypted_content,
        "timestamp": datetime.now()
    })

def get_entries(password):
    entries = db.collection("journal_entries").order_by("timestamp", direction=firestore.Query.DESCENDING).get()
    decrypted_entries = []
    for entry in entries:
        data = entry.to_dict()
        try:
            decrypted_title = decrypt_text(data['title'], password)
            decrypted_content = decrypt_text(data['content'], password)
            decrypted_entries.append({
                "id": entry.id,
                "title": decrypted_title,
                "content": decrypted_content,
                "timestamp": data['timestamp']
            })
        except:
            st.error(f"Failed to decrypt entry {entry.id}. Skipping.")
    return decrypted_entries

def update_entry(doc_id, title, content, password):
    encrypted_title = encrypt_text(title, password)
    encrypted_content = encrypt_text(content, password)
    doc_ref = db.collection("journal_entries").document(doc_id)
    doc_ref.update({
        "title": encrypted_title,
        "content": encrypted_content,
        "timestamp": datetime.now()
    })

def delete_entry(doc_id):
    db.collection("journal_entries").document(doc_id).delete()

def get_chatgpt_feedback(entry_content):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful therapist providing brief feedback on journal entries. Keep your response to 300 characters or less."},
                {"role": "user", "content": f"Please provide brief therapeutic feedback on this journal entry: {entry_content}"}
            ],
            model="gpt-3.5-turbo",
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error getting feedback: {str(e)}"

st.title("Free Writing App")

# Password input
password = st.text_input("Enter your password", type="password")

if password:
    # Sidebar for adding new entries
    st.sidebar.header("Add New Entry")
    new_title = st.sidebar.text_input("Title")
    new_content = st.sidebar.text_area("Content")
    if st.sidebar.button("Add Entry"):
        add_entry(new_title, new_content, password)
        st.sidebar.success("Entry added successfully!")
        st.rerun()

    # Main area for displaying and managing entries
    entries = get_entries(password)
    for entry in entries:
        with st.expander(f"{entry['title']} - {entry['timestamp'].strftime('%Y-%m-%d %H:%M')}"):
            st.write(entry['content'])
            
            # Get and display ChatGPT feedback
            feedback = get_chatgpt_feedback(entry['content'])
            st.write("Therapist's Feedback:")
            st.info(feedback)
            
            # Update functionality
            update_title = st.text_input("Update Title", value=entry['title'], key=f"update_title_{entry['id']}")
            update_content = st.text_area("Update Content", value=entry['content'], key=f"update_content_{entry['id']}")
            if st.button("Update Entry", key=f"update_button_{entry['id']}"):
                update_entry(entry['id'], update_title, update_content, password)
                st.success("Entry updated successfully!")
                st.rerun()
            
            # Delete functionality
            if st.button("Delete Entry", key=f"delete_button_{entry['id']}"):
                delete_entry(entry['id'])
                st.success("Entry deleted successfully!")
                st.rerun()
else:
    st.warning("Please enter a password to access your journal.")