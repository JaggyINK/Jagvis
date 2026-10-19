from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

def read_file(file_path):
    with open(file_path, "r") as file:
        return file.read()

def ask_llm(historique):
    client = Groq(api_key=os.environ["GROQ_KEY"])
    message_system = {
        "role": "system",
        "content": read_file(file_path="./context.txt")
    }
    derniers_messages = historique[-20:]
    chat_completion = client.chat.completions.create(
        messages=[message_system] + derniers_messages,
        model="openai/gpt-oss-120b",
        include_reasoning=False,
    )
    response = chat_completion.choices[0].message.content
    return response

if __name__ == "__main__":
    question = input("Pose ta question :\n")
    response = ask_llm([{"role": "user", "content": question}])
    print("\n")
    print(response)