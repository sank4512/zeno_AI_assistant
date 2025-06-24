import whisper
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import pyttsx3
import os
import subprocess
import platform
from datetime import datetime
import requests
import wikipedia
import streamlit as st
from langdetect import detect
from gtts import gTTS
import tempfile
import time
import google.generativeai as genai
from translate import Translator
import pygame
import json

# -------------------- Configuration ------------------------
LOCAL_MODE = True
GENAI_API_KEY = "AIzaSyBGzLZFa0NkzSqrC7mymT2Nui5XpdWsnt8"
genai.configure(api_key=GENAI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-pro")

model = whisper.load_model("base")
pygame.init()
SUPPORTED_LANGUAGES = ['en', 'hi', 'fr', 'es', 'de', 'it', 'ja', 'ko', 'zh-cn']

# -------------------- Text-to-Speech ------------------------
def speak(text, lang):
    try:
        if lang not in SUPPORTED_LANGUAGES:
            lang = 'en'
        translator = Translator(to_lang=lang)
        translated = translator.translate(text)
        tts = gTTS(text=translated, lang=lang)
        path = os.path.join(tempfile.gettempdir(), f"speech_{int(time.time()*1000)}.mp3")
        tts.save(path)
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
    except Exception as e:
        st.error("Speech error: " + str(e))

# -------------------- Audio Recording ------------------------
def record_audio():
    duration = 5
    sample_rate = 16000
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()
    path = os.path.join(tempfile.gettempdir(), "temp.wav")
    wav.write(path, sample_rate, recording)
    return path

def transcribe_audio(audio_file):
    result = model.transcribe(audio_file)
    return result["text"]

# -------------------- Web Search ------------------------
def search_duckduckgo(query):
    try:
        res = requests.get(f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1")
        data = res.json()
        if data.get("Abstract"):
            return data["Abstract"]
        elif data.get("RelatedTopics"):
            return data["RelatedTopics"][0].get("Text", "No direct answer found.")
        return "No answer found on DuckDuckGo."
    except Exception as e:
        return f"Error accessing DuckDuckGo: {e}"

def get_fallback_response(query):
    try:
        return wikipedia.summary(query, sentences=2)
    except:
        return search_duckduckgo(query)

def get_gemini_response(prompt):
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "Gemini Error: " + str(e)

# -------------------- Local App Launcher ------------------------
def open_app(app_name):
    apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "chrome": r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "vscode": r"C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe"
    }
    app = apps.get(app_name)
    if app:
        try:
            subprocess.Popen(app if 'chrome' not in app else os.path.expandvars(app))
            return f"Opening {app_name}"
        except:
            return "I couldn't open the app."
    return "App not recognized."

# -------------------- Command Processor ------------------------
def process_command(command, lang):
    command = command.lower()
    if "hello" in command:
        return "Hello! How can I help you?"
    elif "your name" in command:
        return "I am Zeno, your voice assistant."
    elif "time" in command:
        return f"The time is {datetime.now().strftime('%H:%M')}"
    elif "open" in command:
        for app in ["notepad", "calculator", "chrome", "vs code"]:
            if app in command:
                return open_app(app) if LOCAL_MODE else "App launch not available in web mode."
        return "I don't recognize that app."
    elif "exit" in command or "quit" in command:
        return "Goodbye!"
    else:
        fallback = get_fallback_response(command)
        if fallback and len(fallback.strip()) > 20:
            return fallback
        return get_gemini_response(command)

# -------------------- Authentication ------------------------
def load_users():
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f)

users = load_users()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "show_login" not in st.session_state:
    st.session_state.show_login = True

if not st.session_state.authenticated:
    st.set_page_config(page_title="Zeno Assistant", layout="centered")
    st.title("🔐 Login" if st.session_state.show_login else "🔐 Sign Up")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    submit = st.button("Submit")
    toggle = st.button("Don't have an account? Sign Up" if st.session_state.show_login else "Already have an account? Login")

    if toggle:
        st.session_state.show_login = not st.session_state.show_login
        st.experimental_rerun()

    if submit:
        if st.session_state.show_login:
            if username in users and users[username] == password:
                st.success("Login successful!")
                st.session_state.authenticated = True
                st.session_state.user = username
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")
        else:
            if username in users:
                st.error("Username already exists")
            else:
                users[username] = password
                save_users(users)
                st.success("Account created. Please login.")
                st.session_state.show_login = True
                st.experimental_rerun()

    st.stop()

# -------------------- Streamlit Clean UI ------------------------
st.set_page_config(page_title="Zeno Assistant", layout="wide")
st.markdown("""
    <style>
        body {
            background-color: #f5f5f5;
            color: #000;
        }
        .main-content {
            padding: 2rem 4rem;
        }
        .input-box {
            width: 60%;
            margin: auto;
            margin-bottom: 2rem;
        }
        .chat-container {
            width: 60%;
            margin: auto;
            background-color: #eae6f8;
            padding: 1.5rem;
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""<h2 style='text-align:center;'>🤖 Zeno – AI Assistant</h2>""", unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.container():
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for role, msg in st.session_state.chat_history:
        st.markdown(f"**{role.capitalize()}**: {msg}")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='input-box'>", unsafe_allow_html=True)
text_input = st.text_input("Message", placeholder="Type your message here...")
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("Send"):
        if text_input:
            lang = detect(text_input)
            st.session_state.chat_history.append(("user", text_input))
            result = process_command(text_input, lang)
            st.session_state.chat_history.append(("zeno", result))
            st.write(f"**Zeno:** {result}")
            speak(result, lang)

with col2:
    if st.button("🎤 Record"):
        audio_file = record_audio()
        query = transcribe_audio(audio_file)
        lang = detect(query)
        st.session_state.chat_history.append(("user", query))
        result = process_command(query, lang)
        st.session_state.chat_history.append(("zeno", result))
        st.write(f"**Zeno:** {result}")
        speak(result, lang)

st.markdown("</div>", unsafe_allow_html=True)

st.caption("Built using Whisper, Gemini, Wikipedia & Streamlit – Zeno AI")
