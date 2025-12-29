import streamlit as st
from google import genai
import tempfile
import os
import pymongo
import json
import uuid
import datetime
import certifi

st.header("LLM-Backend-Prototype")
    
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key = st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def get_mongo_connection():
    client = pymongo.MongoClient(
        st.secrets["MONGO_URI"],
        tlsCAFile = certifi.where()
    )
    db = client["llm_app_db"]
    return db["chats"]

chats_collection = get_mongo_connection()

def create_new_session(user_id):
    if chats_collection is None: return str(uuid.uuid4())[:8]
    new_id = str(uuid.uuid4())[:8]
    doc = {
        "_id": new_id,
        "user_id": user_id,
        "history": [],
        "created_at": datetime.datetime.utcnow()
    }
    chats_collection.insert_one(doc)
    return new_id

def get_user_sessions(user_id):
    if chats_collection is None: return []
    cursor = chats_collection.find(
        {"user_id": user_id},
        {"_id" : 1}
    ).sort("created_at", -1)

    return [doc["_id"] for doc in cursor]

def save_session(session_id):
    if chats_collection is None: return

    history_text = st.session_state.messages

    chats_collection.update_one(
        {"_id": session_id},
        {"$set": {"history": history_text}}
    )

def load_session(session_id):
    if chats_collection is None: return False

    doc = chats_collection.find_one({"_id": session_id})
    if doc:
        st.session_state.messages = doc.get("history", [])
        return True
    return False

def handle_user_change():
    st.session_state.messages = []
    st.session_state.file = []
    if "chat" in st.session_state:
        del st.session_state.chat
    
    new_user = st.session_state.user_id_input
    st.session_state.session_id = create_new_session(new_user)

if "messages" not in st.session_state:
    st.session_state.messages = []

def get_history_for_gemini(messages):
    gemini_history = []
    for msg in messages:
        role = "user" if msg["role"] == "human" else "model"
        parts = [msg["contents"]]
        gemini_history.append({
            "role": role,
            "parts": parts
        })
    return gemini_history

if not st.session_state.get("user_id_input"):
    st.warning("Please enter UserID in sidebar to continue.")

with st.sidebar:
    st.subheader("Login")
    user_id = st.text_input("User ID", key = "user_id_input", on_change = handle_user_change)
    if not user_id:
        st.session_state.messages = []
        st.session_state.file = None
        if "chat" in st.session_state: del st.session_state.chat
        if "session_id" in st.session_state: del st.session_state.session_id

        st.stop()
    
    if user_id:
        st.divider()
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"History for **{user_id}**")
        with col2:
            if st.button("➕"):
                st.session_state.session_id = create_new_session(user_id)
                st.session_state.messages = []
                st.session_state.file= []
                if "chat" in st.session_state: del st.session_state.chat
                st.rerun()

        past_sessions = get_user_sessions(user_id)
        for sess_id in past_sessions:
            is_active = (sess_id == st.session_state.session_id)
            btn_type = "primary" if is_active else "secondary"
            if st.button(f"Chat {sess_id}", type = btn_type, key = f"btn_{sess_id}", use_container_width = True):
                if load_session(sess_id):
                    st.session_state.session_id = sess_id
                    st.session_state.file = []
                    if "chat" in st.session_state: del st.session_state.chat
                    st.rerun()
        
    st.divider()

    uploaded_file = st.file_uploader("Upload File")
    if uploaded_file and "file" not in st.session_state:
        with tempfile.NamedTemporaryFile(delete = False, suffix = f".{uploaded_file.name.split(".")[-1]}") as temp:
            with st.spinner("Uploading File"):
                temp.write(uploaded_file.getvalue())
                temp_path = temp.name
                st.session_state.file = st.session_state.client.files.upload(file = temp_path)
                st.success("File Uploded!")
        os.remove(temp_path)
    
    if not uploaded_file and "file" in st.session_state:
        del st.session_state.file

if "user_id_input" not in st.session_state:
    st.warning("Please enter UserID in sidebar to continue.")

if "chat" not in st.session_state:
    history_payload = []
    if "messages" in st.session_state:
        history_payload = get_history_for_gemini(st.session_state.messages)
    
    st.session_state.chat = st.session_state.client.chats.create(
        model = "gemini-2.5-flash",
        history=history_payload
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask Anything"):
    st.session_state.messages.append({"role": "human", "content": prompt})
    with st.chat_message("human"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Generating response"):
            message = [prompt]
            if "file" in st.session_state and st.session_state.file:
                message.append(st.session_state.file)
            response = st.session_state.chat.send_message(message)
            st.markdown(response.text)

    st.session_state.messages.append({"role": "assistant", "content": response.text})

    save_session(st.session_state.session_id)
