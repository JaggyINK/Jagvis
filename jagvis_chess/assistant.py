from jagvis_chess.groq_client import ask_groq, make_groq_client

TEXT_MODEL = "openai/gpt-oss-120b"

INSTRUCTIONS = (
    "You are Jarvis, a chess coach speaking in smart glasses. "
    "In two short sentences, explain why the best move given by the engine is good. "
    "Never suggest another move."
)


class LLMAssistant:
    def __init__(self, model=TEXT_MODEL, client=None):
        self.model = model
        self.client = client or make_groq_client()

    def explain(self, position, evaluation):
        question = (
            f"Position (FEN): {position.fen}\n"
            f"Side to play: {position.turn.value}\n"
            f"Best move: {evaluation.best_move.notation}\n"
            f"Score: {evaluation.score} centipawns for the side to play"
        )
        if evaluation.mate_in is not None:
            question += f"\nMate in {evaluation.mate_in}"
        messages = [
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": question},
        ]
        return ask_groq(self.client, self.model, messages)
