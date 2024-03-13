import os
from uuid import uuid1
import discord
from dotenv import load_dotenv
from honcho import Honcho
from utils import langchain_message_converter
from agents.honcho_fact_memory.chain import SimpleMemoryChain
from agents.curation_buddy.chain import CurationBuddyChain

load_dotenv()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

app_name = 'vince-curation-buddy'

# honcho = Honcho(app_name=app_name, base_url="http://localhost:8000") # uncomment to use local
honcho = Honcho(app_name=app_name)  # uses demo server at https://demo.honcho.dev
honcho.initialize()

bot = discord.Bot(intents=intents)


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")


@bot.event
async def on_member_join(member):
    await member.send(
        f"*Hello {member.name}, welcome to the server! This is a demo bot built with Honcho,* "
        "*implementing a naive version of the memory feature similar to what ChatGPT recently released.* "
        "*To get started, just type a message in this channel and the bot will respond.* "
        "*Over time, it will remember facts about you and use them to make the conversation more personal.* "
        "*You can use the /restart command to restart the conversation at any time.* "
        "*If you have any questions or feedback, feel free to ask in the #honcho channel.* "
        "*Enjoy!*"
    )


@bot.event
async def on_message(message):
    if message.author == bot.user or message.guild is not None:
        return

    user_id = f"discord_{str(message.author.id)}"
    user = honcho.get_or_create_user(user_id)
    location_id = str(message.channel.id)

    sessions = list(user.get_sessions_generator(location_id, is_active=True, reverse=True))
    try:
        collection = user.get_collection(name="discord")
    except Exception:
        collection = user.create_collection(name="discord")

    session = sessions[0] if len(sessions) > 0 else user.create_session(location_id)

    history = list(session.get_messages_generator())[:5]
    chat_history = langchain_message_converter(history)

    inp = message.content
    user_message = session.create_message(is_user=True, content=inp)

    async with message.channel.typing():
        response = await CurationBuddyChain.chat(
            chat_history=chat_history,
            input=inp,
            message=user_message,
            session=session,
            collection=collection
        )
        await message.channel.send(response)

    session.create_message(is_user=False, content=response)


@bot.slash_command(name="restart", description="Restart the Conversation")
async def restart(ctx):
    user_id = f"discord_{str(ctx.author.id)}"
    user = honcho.get_or_create_user(user_id)
    location_id = str(ctx.channel_id)
    sessions = list(user.get_sessions_generator(location_id, reverse=True))
    sessions[0].close() if len(sessions) > 0 else None

    msg = (
        "Great! The conversation has been restarted. What would you like to talk about?"
    )
    await ctx.respond(msg)


bot.run(os.environ["BOT_TOKEN"])
