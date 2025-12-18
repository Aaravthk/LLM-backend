import streamlit as st
from google import genai

st.header("LLM-Backend-Prototype")

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key = st.secrets["GEMINI_API_KEY"])

if "chat" not in st.session_state:
    st.session_state.chat = st.session_state.client.chats.create(model = "gemini-2.5-flash")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask Anything"):
    st.session_state.messages.append({"role": "human", "content": prompt})
    with st.chat_message("human"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Generating response"):
            response = st.session_state.chat.send_message(prompt)
            st.markdown(response.text)

    st.session_state.messages.append({"role": "assistant", "content": response.text})
