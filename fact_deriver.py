import os, asyncio
from dotenv import load_dotenv
from realtime.connection import Socket
from supabase import create_client, Client
from honcho import Honcho
from agents.honcho_fact_memory.chain import SimpleMemoryChain

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ID = os.getenv('SUPABASE_ID')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def callback1(payload, honcho):
    print(payload["record"]["is_user"])
    print(type(payload["record"]["is_user"]))
    if payload["record"]["is_user"]:  # Check if the message is from a user
        session_id = payload["record"]["session_id"]
        message_id = payload["record"]["id"]
        content = payload["record"]["content"]
        user = honcho.get_or_create_user(user_id)
        session = user.get_session(session_id)
        collection = user.get_collection(name="discord")
        print(f"Fact Deriver Collection: {collection}")
        await SimpleMemoryChain.process_user_message(content, session, collection)
    return


if __name__ == "__main__":
    URL = f"wss://{SUPABASE_ID}.supabase.co/realtime/v1/websocket?apikey={SUPABASE_KEY}&vsn=1.0.0"
    s = Socket(URL)
    s.connect()

    channel_1 = s.set_channel("realtime:public:messages")
    channel_1.join().on("INSERT", callback1)
    s.listen()

