import os
from typing import List
from dotenv import load_dotenv
from supabase import Client
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, load_prompt
from langchain_core.output_parsers import NumberedListOutputParser
from langchain_core.messages import HumanMessage

load_dotenv()


SYSTEM_DERIVE_FACTS = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/core/derive_facts.yaml'))
SYSTEM_INTROSPECTION = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/core/introspection.yaml'))
SYSTEM_RESPONSE = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/core/response.yaml'))
SYSTEM_CHECK_DUPS = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/utils/check_dup_facts.yaml'))
SYSTEM_DIALECTIC = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/core/dialectic.yaml'))

class SimpleMemoryChain:
    "Wrapper class for encapsulating the multiple different chains used"
    output_parser = NumberedListOutputParser()
    llm: ChatOpenAI = ChatOpenAI(model_name = "gpt-4")
    system_derive_facts: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_DERIVE_FACTS)
    system_introspection: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_INTROSPECTION)
    system_response: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_RESPONSE)
    system_check_dups: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_CHECK_DUPS)
    system_dialectic: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_DIALECTIC)

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
    async def check_dups(cls, facts: List):
        """Check that we're not storing duplicate facts"""

        check_duplication = ChatPromptTemplate.from_messages([
            cls.system_check_dups
        ])
        query = " ".join(facts)
        # TODO: query the collection directly
        result = collection.query(query=query, top_k=10) 
        existing_facts = [document.content for document in result]
        chain = check_duplication | cls.llm
        response = await chain.ainvoke({
            "existing_facts": existing_facts,
            "facts": facts
        })
        new_facts = cls.output_parser.parse(response.content)
        for fact in new_facts:
            # TODO: Create a document in the collection
            doc = collection.create_document(content=fact)
            print(f"Returned Document: {doc}")
        for fact in new_facts:
            # TODO: create a metamessage for each fact
            session.create_metamessage(message=user_message, metamessage_type="fact", content=fact)
            print(f"Created fact: {fact}")

        return
    
    @classmethod
    async def dialectic_endpoint(cls, agent_input: str) -> str:
        """Take in agent input, retrieve from the collection, respond"""
        # TODO: query the collection directly
        result = collection.query(query=agent_input, top_k=1)
        dialectic_prompt = ChatPromptTemplate.from_messages([
            cls.system_dialectic
        ])
        chain = dialectic_prompt | cls.llm
        response = await chain.ainvoke({
            "agent_input": agent_input,
            "retrieved_facts": result[0].content if result else "None"
        })
        return response.content

    @classmethod
    async def process_user_message(cls, content: str, supabase: Client, session_id: str, user_id: str, message_id: str):
        # Example: Derive facts from the user input
        facts = await cls.derive_facts(chat_history=[], input=content)
        # Example: Check for duplicate facts
        # TODO: fix what gets passed in here
        await cls.check_dups(user_message=content, facts=facts)
    