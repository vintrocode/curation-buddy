import os, asyncio
from dotenv import load_dotenv
from realtime.connection import Socket
from supabase import create_client, Client
from chain import SimpleMemoryChain

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ID = os.getenv('SUPABASE_ID')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def callback1(payload):
    print(payload["record"]["is_user"])
    print(type(payload["record"]["is_user"]))
    if payload["record"]["is_user"]:  # Check if the message is from a user
        session_id = payload["record"]["session_id"]
        message_id = payload["record"]["id"]
        content = payload["record"]["content"]

        # Example of querying for a user_id based on session_id, adjust according to your schema
        user_response = supabase.table("sessions").select("user_id").eq("id", session_id).execute()
        user_data = user_response.data
        if user_data:
            user_id = user_data[0]['id']  # Assuming 'id' is the field for user_id in your users table
            print(f"User ID: {user_id}")
        else:
            user_id = None

        await SimpleMemoryChain.process_user_message(content, supabase, session_id, user_id, message_id)
    return



if __name__ == "__main__":
    URL = f"wss://{SUPABASE_ID}.supabase.co/realtime/v1/websocket?apikey={SUPABASE_KEY}&vsn=1.0.0"
    s = Socket(URL)
    s.connect()

    channel_1 = s.set_channel("realtime:public:messages")
    channel_1.join().on("INSERT", callback1)
    s.listen()

