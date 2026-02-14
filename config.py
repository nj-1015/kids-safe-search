import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Support both .env (local) and Streamlit Cloud secrets
try:
    import streamlit as st
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
except Exception:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def load_whitelist() -> list[dict]:
    whitelist_path = Path(__file__).parent / "whitelist.json"
    with open(whitelist_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["sites"]
