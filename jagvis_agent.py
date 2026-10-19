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

def construire_contexte(resume, souvenirs):
    contexte = read_file(file_path="./context.txt")
    if souvenirs:
        liste = "\n".join(f"- {souvenir}" for souvenir in souvenirs)
        contexte += f"\n\n## Ce que tu sais déjà sur l'utilisateur\n\n{liste}"
    if resume:
        contexte += f"\n\n## Résumé du début de cette conversation\n\n{resume}"
    return contexte

def ask_llm(historique, resume="", souvenirs=()):
    message_system = {
        "role": "system",
        "content": construire_contexte(resume, souvenirs)
    }
    flux = client.chat.completions.create(
        messages=[message_system] + historique,
        model=MODELE,
        include_reasoning=False,
        stream=True,
    )
    for morceau in flux:
        texte = morceau.choices[0].delta.content
        if texte:
            yield texte

def generer_titre(question, reponse):
    consigne = (
        "Donne un titre court (6 mots maximum) à cette conversation. "
        "Réponds uniquement par le titre, sans guillemets ni ponctuation finale.\n\n"
        f"Question : {question}\n\nRéponse : {reponse[:1000]}"
    )
    return demander([{"role": "user", "content": consigne}])[:60]

def formater(messages):
    noms = {"user": "Utilisateur", "assistant": "Jagvis"}
    return "\n\n".join(f"{noms[message['role']]} : {message['content']}" for message in messages)

def resumer(ancien_resume, messages):
    consigne = (
        "Tu tiens à jour le résumé d'une conversation entre un utilisateur et Jagvis, son mentor. "
        "Intègre les nouveaux échanges au résumé existant. Garde les faits, les décisions, "
        "les questions posées et les conseils donnés. 15 lignes maximum. "
        "Réponds uniquement par le nouveau résumé.\n\n"
        f"Résumé existant :\n{ancien_resume or '(aucun)'}\n\n"
        f"Nouveaux échanges :\n{formater(messages)}"
    )
    return demander([{"role": "user", "content": consigne}])

def extraire_souvenirs(question, souvenirs):
    connus = "\n".join(f"- {souvenir}" for souvenir in souvenirs) or "(aucun)"
    consigne = (
        "Voici un message de l'utilisateur. Repère les informations durables sur lui qui "
        "seront utiles dans de futures conversations : prénom, métier, études, entreprise, "
        "projets, objectifs, préférences. Ignore les questions ponctuelles et ce qui est déjà connu.\n"
        "Écris une information par ligne, sous forme de phrase courte qui commence par "
        "« L'utilisateur ». Ne devine jamais son genre. "
        "S'il n'y a rien de nouveau, réponds exactement AUCUN.\n\n"
        f"Déjà connu :\n{connus}\n\nMessage : {question}"
    )
    reponse = demander([{"role": "user", "content": consigne}])
    if reponse.upper().startswith("AUCUN"):
        return []
    return [ligne.strip("-• ").strip() for ligne in reponse.splitlines() if ligne.strip("-• ").strip()]

if __name__ == "__main__":
    question = input("Pose ta question :\n")
    print("\n")
    for texte in ask_llm([{"role": "user", "content": question}]):
        print(texte, end="", flush=True)
    print()
