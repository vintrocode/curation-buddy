import os
from typing import List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, load_prompt
from langchain_core.output_parsers import NumberedListOutputParser
from langchain_core.messages import HumanMessage
from realtime.connection import Socket

from honcho import Collection, Session, Message

load_dotenv()

SUPABASE_ID = os.getenv('SUPABASE_ID')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SYSTEM_DERIVE_FACTS = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/core/derive_facts.yaml'))
SYSTEM_INTROSPECTION = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/core/introspection.yaml'))
SYSTEM_RESPONSE = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/core/response.yaml'))
SYSTEM_CHECK_DUPS = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/utils/check_dup_facts.yaml'))

class SimpleMemoryChain:
    "Wrapper class for encapsulating the multiple different chains used"
    output_parser = NumberedListOutputParser()
    llm: ChatOpenAI = ChatOpenAI(model_name = "gpt-3.5-turbo")
    system_derive_facts: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_DERIVE_FACTS)
    system_introspection: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_INTROSPECTION)
    system_response: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_RESPONSE)
    system_check_dups: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_CHECK_DUPS)

    def __init__(self) -> None:
        pass

    @classmethod
    async def derive_facts(cls, chat_history: List, input: str):
        """Derive facts from the user input"""

        fact_derivation = ChatPromptTemplate.from_messages([
            cls.system_derive_facts
        ])
        chain = fact_derivation | cls.llm
        response = await chain.ainvoke({
            "chat_history": [("user: " + message.content if isinstance(message, HumanMessage) else "ai: " + message.content) for message in chat_history],
            "user_input": input
        })
        facts = cls.output_parser.parse(response.content)

        return facts
    
    @classmethod
    async def check_dups(cls, user_message: Message, session: Session, collection: Collection, facts: List):
        """Check that we're not storing duplicate facts"""

        check_duplication = ChatPromptTemplate.from_messages([
            cls.system_check_dups
        ])
        query = " ".join(facts)
        result = collection.query(query=query, top_k=10) 
        existing_facts = [document.content for document in result]
        chain = check_duplication | cls.llm
        response = await chain.ainvoke({
            "existing_facts": existing_facts,
            "facts": facts
        })
        new_facts = cls.output_parser.parse(response.content)
        for fact in new_facts:
            collection.create_document(content=fact)
        for fact in new_facts:
            session.create_metamessage(message=user_message, metamessage_type="fact", content=fact)

        return
    

def callback1(payload):
    print("Got messages")
    print("Callback 1: ", payload)


if __name__ == "__main__":
    URL = f"wss://{SUPABASE_ID}.supabase.co/realtime/v1/websocket?apikey={SUPABASE_KEY}&vsn=1.0.0"
    s = Socket(URL)
    s.connect()

    channel_1 = s.set_channel("realtime:public:messages")
    channel_1.join().on("INSERT", callback1)
    s.listen()