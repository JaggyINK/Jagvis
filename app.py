import streamlit as st
from llm_agent import ConversationAgent


class ChatInterface:
	def __init__(self):
		st.set_page_config(page_title="Jarvis")
		st.title("Barbe-Quasar")
		self.agent = self.get_agent()


	@staticmethod
	def get_agent():
		if "agent" not in st.session_state:
			st.session_state.agent = ConversationAgent()
		return st.session_state.agent


	@staticmethod
	def display_message(role, content):
		with st.chat_message(role):
			st.markdown(content)


	def display_conversation_history(self):
		for message in self.agent.get_displayable_history():
			self.display_message(role=message["role"], content=message["content"])


	def handle_user_input(self, user_input):
		self.display_message(role="user", content=user_input)
		response = self.agent.ask_llm(user_input)
		self.display_message(role="assistant", content=response)


	def run(self):
		self.display_conversation_history()

		user_input = st.chat_input(
			"Que veux tu moussaillon ?",
			accept_file=False,
			)

		if user_input :
			self.handle_user_input(user_input)


ChatInterface().run()
