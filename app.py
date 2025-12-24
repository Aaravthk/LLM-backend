import streamlit as st
from google import genai
import tempfile
import os
import redis
import json
import uuid

st.header("LLM-Backend-Prototype")
    
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key = st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def get_redis_connection():
    return redis.Redis.from_url(st.secrets["REDIS_URL"], decode_responses = True)

redis_client = get_redis_connection()

def save_session(session_id):
    data = {
        "messages" : st.session_state.messages
    }
    redis_client.set(session_id, json.dumps(data))

def load_session(session_id):
    data = redis_client.get(session_id)
    if data:
        parsed = json.loads(data)
        st.session_state.messages = parsed["messages"]
        return True
    return False

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

if "chat" not in st.session_state:
    history_payload = []
    if "messages" in st.session_state:
        history_payload = get_history_for_gemini(st.session_state.messages)
    
    st.session_state.chat = st.session_state.client.chats.create(
        model = "gemini-2.5-flash",
        history=history_payload
    )

with st.sidebar:
    st.header("Session Manager")
    mode = st.radio("Choose Mode", ["+ New Chat", "Resume Chat"])
    if mode == "+ New Chat":
        if st.button("Start New Session"):
            new_id = str(uuid.uuid4())[:8]
            st.session_state.session_id = new_id
            st.session_state.messages = []
            st.session_state.file = None
            st.rerun()
    elif mode == "Resume Chat":
        session_id = st.text_input("Enter Session ID")
        if st.button("Load Chat"):
            with st.spinner("Loading chat"):
                if load_session(session_id):
                    st.session_state.session_id = session_id
                    st.session_state.loaded = True
                    st.rerun()
                else:
                    st.error("Session ID not found!")
    
    if st.session_state.get("loaded"):
        st.success(f"Successfully loaded!")
        del st.session_state.loaded

    if "session_id" in st.session_state:
        st.caption(f"Current session ID: `{st.session_state.session_id}`")
        st.caption("Save this ID to resume this chapter later")
    else:
        st.session_state.session_id = str(uuid.uuid4())[:8]
        
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

    if "session_id" in st.session_state:
        save_session(st.session_state.session_id)
