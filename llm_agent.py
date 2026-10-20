from groq import Groq

from dotenv import load_dotenv
import os


class ConversationAgent:
    def __init__(self):
        load_dotenv()
        self.groq_client = Groq(api_key=os.environ["GROQ_KEY"])
        self.conversation_history = [
                {
                    "role": "system",
                    "content": self.read_file(file_path="./context.txt")
                }
            ]


    @staticmethod
    def read_file(file_path):
        with open(file_path, "r") as file:
            return file.read()


    def update_conversation_history(self, role, content):
        self.conversation_history.append(
            {
            "role": role,
            "content": content,
            }
        )


    def get_displayable_history(self):
        return [
            message for message in self.conversation_history
            if message["role"] != "system"
        ]


    def ask_llm(self, question):

        self.update_conversation_history(role="user", content=question)

        response = self.groq_client.chat.completions.create(
            messages=self.conversation_history,
            model="openai/gpt-oss-120b",
            include_reasoning=False,
        ).choices[0].message.content


        self.update_conversation_history(role="assistant", content=response)

        return response





























if __name__ == "__main__":
    question = input("Pose ta question :\n")
    agent = ConversationAgent()
    response = agent.ask_llm(question)
    print("\n")
    print(response)