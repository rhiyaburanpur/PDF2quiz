import streamlit as st

st.title("Temp Streamlit App")
name = st.text_input("Enter your name:")
if name:
    st.write(f"Hello, {name}!")