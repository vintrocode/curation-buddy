import os, asyncio
from dotenv import load_dotenv
from realtime.connection import Socket
from honcho import Honcho
from agents.honcho_fact_memory.chain import SimpleMemoryChain

load_dotenv()

SUPABASE_ID = os.getenv('SUPABASE_ID')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

async def callback1(payload, honcho):
    if payload["record"]["is_user"] == "True":  # Check if the message is from a user
        session_id = payload["record"]["session_id"]
        user_id = payload["record"]["id"]
        content = payload["record"]["content"]
        user = honcho.get_or_create_user(user_id)
        session = user.get_session(session_id)
        collection = user.get_collection(name="discord") 
        await SimpleMemoryChain.process_user_message(content, session, collection)
    return


if __name__ == "__main__":
    app_name = "vince-fact-deriver"
    honcho = Honcho(app_name)
    honcho.initialize()
    URL = f"wss://{SUPABASE_ID}.supabase.co/realtime/v1/websocket?apikey={SUPABASE_KEY}&vsn=1.0.0"
    s = Socket(URL)
    s.connect()

    channel_1 = s.set_channel("realtime:public:messages")
    channel_1.join().on("INSERT", lambda payload: asyncio.create_task(callback1(payload, honcho)))
    s.listen()

