# Jagvis

Assistant conversationnel inspiré de J.A.R.V.I.S. : une interface Streamlit qui
discute avec un LLM via l'API Groq, garde les conversations dans une base SQLite,
résume les longs échanges et se souvient de l'utilisateur.

## Lancer le projet

```bash
pip install -r requirements.txt
echo "GROQ_KEY=ta_cle_groq" > .env
streamlit run app.py
```
