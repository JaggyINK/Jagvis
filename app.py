import groq
import streamlit as st
import db
from jagvis_agent import ask_llm, extraire_souvenirs, generer_titre, resumer

TAILLE_FENETRE = 20
SEUIL_RESUME = 30

st.set_page_config(page_title="Jagvis")
st.title("Jagvis")

db.initialiser()

def mettre_a_jour_resume(conversation_id, messages):
	resume, nb_messages_resumes = db.lire_resume(conversation_id)
	non_resumes = messages[nb_messages_resumes:]
	if len(non_resumes) <= SEUIL_RESUME:
		return
	a_resumer = non_resumes[:-TAILLE_FENETRE]
	nouveau_resume = resumer(resume, a_resumer)
	db.enregistrer_resume(conversation_id, nouveau_resume, nb_messages_resumes + len(a_resumer))

def memoriser(question):
	souvenirs = [souvenir["contenu"] for souvenir in db.lister_souvenirs()]
	for souvenir in extraire_souvenirs(question, souvenirs):
		db.ajouter_souvenir(souvenir)

if "actuelle" not in st.session_state:
	st.session_state.actuelle = None

with st.sidebar:
	if st.button("Nouvelle conversation", width="stretch"):
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
			width="stretch",
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
	souvenirs = db.lister_souvenirs()
	with st.expander(f"🧠 Ce que Jagvis sait de toi ({len(souvenirs)})"):
		if not souvenirs:
			st.caption("Rien pour l'instant. Parle-lui de toi !")
		for souvenir in souvenirs:
			colonne_texte, colonne_supprimer = st.columns([5, 1])
			colonne_texte.write(souvenir["contenu"])
			if colonne_supprimer.button("✕", key=f"souvenir_{souvenir['id']}"):
				db.supprimer_souvenir(souvenir["id"])
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
	try:
		resume, nb_messages_resumes = db.lire_resume(st.session_state.actuelle)
		souvenirs = [souvenir["contenu"] for souvenir in db.lister_souvenirs()]
		with st.chat_message("assistant"):
			response = st.write_stream(
				ask_llm(messages[nb_messages_resumes:], resume, souvenirs)
			)
		db.ajouter_message(st.session_state.actuelle, "assistant", response)
		messages.append({"role": "assistant", "content": response})
		with st.spinner("Jagvis prend des notes…"):
			if nouvelle_conversation:
				db.renommer_conversation(st.session_state.actuelle, generer_titre(user_input, response))
			memoriser(user_input)
			mettre_a_jour_resume(st.session_state.actuelle, messages)
		st.rerun()
	except groq.AuthenticationError:
		st.error("La clé API Groq est invalide. Vérifie GROQ_KEY dans le fichier .env.")
	except groq.RateLimitError:
		st.error("Trop de requêtes envoyées à Groq. Attends un peu puis réessaie.")
	except groq.APIConnectionError:
		st.error("Impossible de joindre Groq. Vérifie ta connexion internet.")
	except groq.APIError as erreur:
		st.error(f"Groq a renvoyé une erreur : {erreur}")
