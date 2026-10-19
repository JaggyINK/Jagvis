from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

MODELE = "openai/gpt-oss-120b"

client = Groq(api_key=os.environ["GROQ_KEY"])

def read_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def demander(messages):
    chat_completion = client.chat.completions.create(
        messages=messages,
        model=MODELE,
        include_reasoning=False,
    )
    return chat_completion.choices[0].message.content.strip()

def ask_llm(historique):
    message_system = {
        "role": "system",
        "content": read_file(file_path="./context.txt")
    }
    derniers_messages = historique[-20:]
    return demander([message_system] + derniers_messages)

def generer_titre(question, reponse):
    consigne = (
        "Donne un titre court (6 mots maximum) à cette conversation. "
        "Réponds uniquement par le titre, sans guillemets ni ponctuation finale.\n\n"
        f"Question : {question}\n\nRéponse : {reponse[:1000]}"
    )
    return demander([{"role": "user", "content": consigne}])[:60]

if __name__ == "__main__":
    question = input("Pose ta question :\n")
    response = ask_llm([{"role": "user", "content": question}])
    print("\n")
    print(response)
