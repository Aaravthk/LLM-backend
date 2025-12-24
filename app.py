import streamlit as st
from google import genai
from google.genai import types
import tempfile
import os

st.header("LLM-Backend-Prototype")
    
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key = st.secrets["GEMINI_API_KEY"])

if "chat" not in st.session_state:
    st.session_state.chat = st.session_state.client.chats.create(model = "gemini-2.5-flash")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
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
            if st.session_state.file:
                message.append(st.session_state.file)
            response = st.session_state.chat.send_message(message)
            st.markdown(response.text)

    st.session_state.messages.append({"role": "assistant", "content": response.text})
