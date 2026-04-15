import streamlit as st
from db_config import validate_db_config

@st.cache_resource
def init():
    mode = validate_db_config()
    return mode

mode = init()
st.write(f"Database mode: {mode}")
