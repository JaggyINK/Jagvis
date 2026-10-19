import streamlit as st
import db
from llm_agent import ask_llm

st.set_page_config(page_title="Jagvis")
st.title("Jagvis")

db.initialiser()

if "actuelle" not in st.session_state:
	st.session_state.actuelle = None

with st.sidebar:
	if st.button("Nouvelle conversation"):
		st.session_state.actuelle = None
	st.subheader("Historique")
	for conversation in db.lister_conversations():
		if st.button(conversation["titre"], key=f"conversation_{conversation['id']}"):
			st.session_state.actuelle = conversation["id"]

if st.session_state.actuelle is None:
	messages = []

else:
	messages = db.lire_messages(st.session_state.actuelle)

for message in messages:
	with st.chat_message(message["role"]):
		st.markdown(message["content"])

user_input = st.chat_input(
	"Bonjour Jag, en quoi puis-je t'aider ?",
	accept_file=False
	)
if user_input :
	if st.session_state.actuelle is None:
		st.session_state.actuelle = db.creer_conversation(user_input[:40])
	with st.chat_message("user"):
		st.markdown(user_input)
	db.ajouter_message(st.session_state.actuelle, "user", user_input)
	messages.append(
		{"role": "user", "content": user_input}
		)
	response = ask_llm(messages)
	with st.chat_message("assistant"):
		st.markdown(response)
	db.ajouter_message(st.session_state.actuelle, "assistant", response)
	st.rerun()
