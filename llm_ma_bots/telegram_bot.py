import logging
import os
from collections import defaultdict
import signal
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler
from groq import Groq

load_dotenv()
client = Groq()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# This dictionary stores the messages. The key is the chat_id and the value is a list of messages.
chat_history = defaultdict(list)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hi I'm a bot, how can I help?")

async def update_and_get_chat_history(message: str, chat_id: int, top_k_messages: int = 5) -> list:
    chat_history[chat_id].append(message)
    return chat_history[chat_id][-top_k_messages:-1]

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE, with_context: bool = True):
    chat_id = update.effective_chat.id
    message = update.effective_message.text

    history = await update_and_get_chat_history(message, chat_id)

    if with_context:
        str_history = "\n".join(history)
        formatted_prompt = f"Recent user messages:\n\n{str_history}\n\nUser message to answer:\n\n{message}"
        system_prompt = "You are a friendly journal buddy 📔✨. Keep the conversation light and match the user's tone, including using emojis when they do 😊. Use their recent recent messages as context to provide personalized responses."
    else:
        formatted_prompt = message
        system_prompt = "You are a friendly journal buddy 📔✨. Keep the conversation light and match the user's tone, including using emojis when they do 😊. Encourage the user to share more about their day by asking open-ended questions and showing interest in their experiences."

    completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": formatted_prompt},
        ],
        temperature=0.7,
        max_tokens=4080,
        top_p=1,
        stream=False,
        stop=None,
    )

    # Check if the message content is non-empty before sending
    if completion.choices[0].message.content.strip():
        await context.bot.send_message(chat_id=update.effective_chat.id, text=completion.choices[0].message.content)
    else:
        logging.error("Attempted to send an empty message.")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I couldn't process your request.")
def stop_handler(signal, frame):
    logging.info("Signal received, stopping the bot.")
    application.stop()

def main():
    global application
    application = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    message_handler = MessageHandler(None, ai_chat)
    application.add_handler(message_handler)

    # Handle signals for graceful shutdown
    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
