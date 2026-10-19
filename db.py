import json
import os
import sqlite3

FICHIER_DB = "jagvis.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	titre TEXT NOT NULL,
	cree_le TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
	role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
	contenu TEXT NOT NULL,
	cree_le TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
"""

def connexion():
	conn = sqlite3.connect(FICHIER_DB)
	conn.row_factory = sqlite3.Row
	conn.execute("PRAGMA foreign_keys = ON")
	return conn

def initialiser():
	with connexion() as conn:
		conn.executescript(SCHEMA)

def lister_conversations():
	with connexion() as conn:
		lignes = conn.execute(
			"SELECT id, titre FROM conversations ORDER BY id DESC"
		).fetchall()
	return [dict(ligne) for ligne in lignes]

def creer_conversation(titre):
	with connexion() as conn:
		curseur = conn.execute(
			"INSERT INTO conversations (titre) VALUES (?)", (titre,)
		)
	return curseur.lastrowid

def lire_messages(conversation_id):
	with connexion() as conn:
		lignes = conn.execute(
			"SELECT role, contenu FROM messages WHERE conversation_id = ? ORDER BY id",
			(conversation_id,),
		).fetchall()
	return [{"role": ligne["role"], "content": ligne["contenu"]} for ligne in lignes]

def ajouter_message(conversation_id, role, contenu):
	with connexion() as conn:
		conn.execute(
			"INSERT INTO messages (conversation_id, role, contenu) VALUES (?, ?, ?)",
			(conversation_id, role, contenu),
		)

def importer_json(fichier_json):
	with open(fichier_json, "r", encoding="utf-8") as fichier:
		conversations = json.load(fichier)
	for conversation in conversations:
		conversation_id = creer_conversation(conversation["titre"])
		for message in conversation["messages"]:
			ajouter_message(conversation_id, message["role"], message["content"])
	return len(conversations)

if __name__ == "__main__":
	initialiser()
	if os.path.exists("conv.json") and not lister_conversations():
		nombre = importer_json("conv.json")
		print(f"{nombre} conversations importées depuis conv.json")
	else:
		print("Base prête, rien à importer")
