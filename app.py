import streamlit as st
import db
from llm_agent import ask_llm, generer_titre

st.set_page_config(page_title="Jagvis")
st.title("Jagvis")

db.initialiser()

if "actuelle" not in st.session_state:
	st.session_state.actuelle = None

with st.sidebar:
	if st.button("Nouvelle conversation", use_container_width=True):
		st.session_state.actuelle = None
		st.rerun()
	st.subheader("Historique")
	for conversation in db.lister_conversations():
		identifiant = conversation["id"]
		colonne_titre, colonne_options = st.columns([5, 1])
		est_ouverte = identifiant == st.session_state.actuelle
		if colonne_titre.button(
			conversation["titre"],
			key=f"conversation_{identifiant}",
			type="primary" if est_ouverte else "secondary",
			use_container_width=True,
		):
			st.session_state.actuelle = identifiant
			st.rerun()
		with colonne_options.popover("⋯"):
			nouveau_titre = st.text_input(
				"Titre", value=conversation["titre"], key=f"titre_{identifiant}"
			)
			if st.button("Renommer", key=f"renommer_{identifiant}"):
				db.renommer_conversation(identifiant, nouveau_titre.strip() or conversation["titre"])
				st.rerun()
			if st.button("🗑️ Supprimer", key=f"supprimer_{identifiant}"):
				db.supprimer_conversation(identifiant)
				if est_ouverte:
					st.session_state.actuelle = None
				st.rerun()

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
	nouvelle_conversation = st.session_state.actuelle is None
	if nouvelle_conversation:
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
	if nouvelle_conversation:
		db.renommer_conversation(st.session_state.actuelle, generer_titre(user_input, response))
	st.rerun()
