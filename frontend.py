import os
import time

import streamlit as st

from common.llm_client import LLMClient, Model, Provider

# Set environment variables from secrets.
os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

# Get a session state
st.session_state.setdefault("time", 0)

st.title("Pardon My English")

st.write(
    "Hi there! I'm an app designed to assist you in rephrasing your text into polished English. "
    "Please type whatever you want to be rewritten, and I'll rework it into proper English for you."
)

input_text = st.text_area("Type your text here:", height=200)
rewrite_button = st.button("Rewrite")


# Set the provider and model for the LLM client.
provider = Provider.GROQ
model = Model.LLAMA3_70B


# Initialize the LLM client and cache it.
@st.cache_resource
def get_llm_client():
    return LLMClient(provider=provider, model=model)


llm_client = get_llm_client()


# Print the nerdy details of the LLM client.
def print_nerdy_details(num_tokens: int):
    st.write("Nerdy Details:")
    details = f"""
    Provider: {provider.value}
    Model: {model.value}
    Total Tokens Used: {num_tokens}
    """
    st.code(details, language="text")


# When the user clicks the "Rewrite" button, the app will rewrite the text.
if rewrite_button:
    if time.time() - st.session_state["time"] < 5:
        st.error("Please wait 5 seconds before rewriting another text.")
        st.stop()
    else:
        with st.spinner("Rewriting..."):
            rewritten_text, total_tokens_used = llm_client.rewrite(input_text)
            st.markdown("---")
            st.markdown(f"{rewritten_text}")
            st.session_state["time"] = time.time()
            st.markdown("---")
            print_nerdy_details(total_tokens_used)
