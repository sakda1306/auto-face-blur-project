"""Streamlit web UI for Auto Face Blur. See docs/CONTRACT.md section 4."""

import streamlit as st

from detector import blur_faces

st.title("Auto Face Blur")

tab_image, tab_live = st.tabs(["Image", "Live Webcam"])
