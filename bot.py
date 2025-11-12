import os
import sqlite3
import datetime
import asyncio
import tempfile
import logging
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters
import openai
import parser  # <-- o arquivo parser.py que você já tem
import whisper

model = whisper.load_model("small")  # ou "base", "tiny", "medium", "large"

def transcrever_audio_local(audio_path):
    result = model.transcribe(audio_path, language="pt")
    return result["text"]

logging.basicConfig(level=logging.INFO)

# Banco de dados local
DB_PATH = "gymtracker.db"
TOKEN = os.getenv("GYMTRACKER_TOKEN_BOT")

# Inicializa banco se ainda não existir
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            action TEXT,
            exercise TEXT,
            exercise_raw TEXT,
            weight REAL,
            reps INTEGER,
            raw_text TEXT
        );
        """)
    logging.info("✅ Banco de dados inicializado")

def insert_entry(action, exercise, exercise_raw, weight, reps, raw_text):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO logs (timestamp, action, exercise, exercise_raw, weight, reps, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.datetime.now().isoformat(),
            action,
            exercise,
            exercise_raw,
            weight,
            reps,
            raw_text
        ))
        conn.commit()


# --------------------------
# Telegram + Whisper Offline
# --------------------------

openai.api_key = os.getenv("OPENAI_API_KEY")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Baixa o áudio
        file = await context.bot.get_file(update.message.voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            audio_path = tmp.name

        # Transcreve com Whisper
        #with open(audio_path, "rb") as f:
        #    transcript = openai.audio.transcriptions.create(
        #        model="gpt-4o-mini-transcribe",
        #        file=f,
        #        language="pt"
        #    )
        #text = transcript.text.strip()

        text = transcrever_audio_local(audio_path).strip()

        logging.info(f"Transcrição: {text}")
        await update.message.reply_text(f"🎧 {text}")

        # Faz o parsing da transcrição
        parsed = parser.parse_command(text)
        logging.info(f"[DEBUG] Resultado do parser: {parsed}")

        action = parsed.get("action")
        exercise = parsed.get("exercise")
        exercise_raw = None
        weight = parsed.get("weight")
        reps = parsed.get("reps")

        # Se for início/final, guarda o texto original como exercise_raw
        if action in ("start", "end"):
            exercise_raw = text.replace("início", "").replace("final", "").strip()

        # Grava no banco
        if action != "unknown":
            insert_entry(
                action=action,
                exercise=exercise,
                exercise_raw=exercise_raw,
                weight=weight,
                reps=reps,
                raw_text=text
            )

        # Resposta amigável
        if action == "start":
            await update.message.reply_text(f"🏋️ Início de **{exercise}** registrado!")
        elif action == "set":
            await update.message.reply_text(f"📊 {weight} kg — {reps} repetições registradas.")
        elif action == "end":
            await update.message.reply_text(f"✅ Final de **{exercise}** registrado!")
        else:
            await update.message.reply_text("🤔 Não entendi bem, pode repetir?")

    except Exception as e:
        logging.exception("Erro ao processar áudio")
        await update.message.reply_text(f"⚠️ Erro: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip().lower()
        logging.info(f"📩 Mensagem de texto recebida: {text}")

        # Faz o parsing
        parsed = parser.parse_command(text)
        logging.info(f"[DEBUG] Resultado do parser: {parsed}")

        action = parsed.get("action")
        exercise = parsed.get("exercise")
        exercise_raw = None
        weight = parsed.get("weight")
        reps = parsed.get("reps")

        if action in ("start", "end"):
            exercise_raw = text.replace("início", "").replace("final", "").strip()

        # Grava no banco
        if action != "unknown":
            insert_entry(
                action=action,
                exercise=exercise,
                exercise_raw=exercise_raw,
                weight=weight,
                reps=reps,
                raw_text=text
            )

        # Resposta amigável
        if action == "start":
            await update.message.reply_text(f"🏋️ Início de **{exercise}** registrado!")
        elif action == "set":
            await update.message.reply_text(f"📊 {weight} kg — {reps} repetições registradas.")
        elif action == "end":
            await update.message.reply_text(f"✅ Final de **{exercise}** registrado!")
        else:
            await update.message.reply_text("🤔 Não entendi bem, pode repetir?")

    except Exception as e:
        logging.exception("Erro ao processar texto")
        await update.message.reply_text(f"⚠️ Erro: {e}")


async def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # Registra os handlers aqui...
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Bot está rodando offline...")
    await app.initialize()   # inicializa manualmente
    await app.start()        # inicia o bot (sem bloquear)
    await app.updater.start_polling()  # inicia polling manualmente

    try:
        # Mantém o loop rodando até CTRL+C
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        print("⏹ Encerrando o bot...")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
