"""Streamlit web UI for Auto Face Blur (image upload only). See docs/CONTRACT.md section 4."""

import streamlit as st

from detector import blur_faces

st.title("Auto Face Blur")
