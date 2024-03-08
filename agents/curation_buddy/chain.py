import os, re
from typing import List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, load_prompt
from langchain_core.output_parsers import NumberedListOutputParser
from langchain_core.messages import HumanMessage
from langchain_community.utilities import ApifyWrapper

from honcho import Collection, Session, Message

load_dotenv()

SYSTEM_THOUGHT = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/thought.yaml'))
SYSTEM_RESPONSE = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/response.yaml'))

# takes user input
#  quick check if it contains a link
#  if it does, get the webpage content and extract the topic. ask a follow up that prods at why they might be interested in it
#  while we feel like we haven't gotten to the bottom of the user's interest, keep engaging with them about it
# generate a thought about the user's needs, list of questions that'd help it know
# parse out those questions, loop over the endpoint asking Honcho about them
# collate those answers, generate a response with those as context

class CurationBuddyChain:
    """Chain for executing the curation buddy logic"""
    apify = ApifyWrapper()
    output_parser = NumberedListOutputParser()
    llm: ChatOpenAI = ChatOpenAI(model_name = "gpt-3.5-turbo")
    system_thought: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_THOUGHT)
    system_response: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_RESPONSE)

    def __init__(self) -> None:
        pass

    @classmethod
    async def check_for_link(cls, input: str) -> List[str]:
        url_pattern = re.compile(r'\b((http|https):\/\/?)[^\s()<>]+(?:\([\w\d]+\)|([^[:punct:]\s]|\/?))')
        urls = re.findall(url_pattern, input)
        return urls
    
    @classmethod
    async def get_webpage_content(cls, links: List[str]) -> List[str]:
        for link in links:
            # Call the Actor to obtain text from the crawled webpages
            loader = cls.apify.call_actor(
                actor_id="apify/website-content-crawler",
                run_input={
                    "startUrls": [{"url": link}]
                },
            )
            data = loader.load()
            print(f"LINK: {link}")
            print(f"DATA: {data}")
            # TODO: should probably have a list of these URLs to avoid redundancy
            # also should probably embed them

    @classmethod
    async def generate_thought(cls, input: str, chat_history: List[str], session: Session) -> str:
        """Generate a thought about the user's input along with a list of questions that'd help it better serve the user"""
        thought_prompt = ChatPromptTemplate.from_messages([
            cls.system_thought
        ])
        chain = thought_prompt | cls.llm
        response = await chain.invoke({
            "input": input,
            "chat_history": chat_history
        })
        # TODO: write to Honcho
        return response.content

    @classmethod
    async def parse_questions(cls, thought: str) -> List[str]:
        """Parse out the questions from the thought"""
        questions = cls.output_parser.parse(thought)
        return questions

    @classmethod
    async def ask_questions(cls, questions: List[str]) -> List[str]:
        """Loop over the questions and ask honcho about them"""
        answers = []
        for question in questions:
            answer = await cls.ask_honcho(question)
            answers.append(answer)
        return answers

    @classmethod
    async def generate_response(cls, input: str, answers: List[str], chat_history: List[str], session: Session) -> str:
        """Collate the answers to the questions and generate a response with those as context"""
        response_prompt = ChatPromptTemplate.from_messages([
            cls.system_response
        ])
        chain = response_prompt | cls.llm
        response = await chain.invoke({
            "input": input,
            "answers": answers,
            "chat_history": chat_history
        })
        # TODO: write to Honcho
        return response.content



    @classmethod
    async def chat(cls, input: str, chat_history: List[str], session: Session) -> str:
        """Chat with the user"""
        urls = await cls.check_for_link(input)
        if urls:
            await cls.get_webpage_content(urls)
            # TODO: probably have a prompt to ask the user about the URLs they posted
            # and then exit the chat function

        thought = await cls.generate_thought(input, chat_history, session)
        questions = await cls.parse_questions(thought)
        answers = await cls.ask_questions(questions)
        response = await cls.generate_response(input, answers, chat_history, session)
        return response
    

