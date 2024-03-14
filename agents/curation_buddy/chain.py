import os, re, aiohttp
from typing import List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, load_prompt
from langchain_core.output_parsers import NumberedListOutputParser
from langchain_community.utilities import ApifyWrapper
from langchain_core.document_loaders.base import Document
from honcho import Session, Message
from utils import langchain_message_unpacker

load_dotenv()

SYSTEM_THOUGHT = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/thought.yaml'))
SYSTEM_RESPONSE = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/response.yaml'))
SYSTEM_RESPONSE_URLS = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/response_urls.yaml'))
SYSTEM_SUMMARIZE = load_prompt(os.path.join(os.path.dirname(__file__), 'prompts/summarize.yaml'))


class CurationBuddyChain:
    """Chain for executing the curation buddy logic"""
    apify = ApifyWrapper()
    output_parser = NumberedListOutputParser()
    gpt_35: ChatOpenAI = ChatOpenAI(model="gpt-3.5-turbo")
    gpt_4: ChatOpenAI = ChatOpenAI(model="gpt-4-turbo-preview")
    system_thought: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_THOUGHT)
    system_response: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_RESPONSE)
    system_response_urls: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_RESPONSE_URLS)
    system_summarize: SystemMessagePromptTemplate = SystemMessagePromptTemplate(prompt=SYSTEM_SUMMARIZE)

    def __init__(self) -> None:
        pass

    @classmethod
    async def check_for_link(cls, input: str) -> List[str]:
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        urls = re.findall(url_pattern, input)
        print(f"LINK(S) DETECTED: {urls}")
        return urls

    @classmethod
    async def get_webpage_content(cls, links: List[str]) -> List[str]:
        docs = []
        for link in links:
            loader = cls.apify.call_actor(
                actor_id="apify/website-content-crawler",
                run_input={"startUrls": [{"url": link}], "maxCrawlPages": 1, "crawlerType": "cheerio"},
                dataset_mapping_function=lambda item: Document(
                    page_content=item["text"] or "", metadata={"source": item["url"]}
                ),
            )
            docs.append(loader.load())
        return docs
    
    @classmethod
    async def summarize_webpage_content(cls, webpage_content: str) -> str:
        """Summarize the webpage content"""
        summarize_prompt = ChatPromptTemplate.from_messages([
            cls.system_summarize
        ])
        chain = summarize_prompt | cls.gpt_4
        response = await chain.ainvoke({
            "webpage_content": webpage_content
        })
        return response.content
    
    @classmethod
    async def generate_response_urls(cls, summaries: List[str], chat_history: List[str]) -> str:
        """Generate a response asking the user about the URLs they posted"""
        response_urls_prompt = ChatPromptTemplate.from_messages([
            cls.system_response_urls
        ])
        chain = response_urls_prompt | cls.gpt_35
        response = await chain.ainvoke({
            "summaries": summaries,
            "chat_history": langchain_message_unpacker(chat_history)
        })
        return response.content

    @classmethod
    async def generate_thought(cls, input: str, chat_history: List[str], max_retries: int = 3) -> str:
        """Generate a thought about the user's input along with a list of questions that'd help it better serve the user"""
        thought_prompt = ChatPromptTemplate.from_messages([
            cls.system_thought
        ])
        chain = thought_prompt | cls.gpt_4
        retries = 0
        while retries < max_retries:
            try:
                response = await chain.ainvoke({
                    "input": input,
                    "chat_history": langchain_message_unpacker(chat_history)
                })
                questions = cls.output_parser.parse(response.content)
                break  # Exit loop if successful
            except Exception as e:
                print(f"Attempt {retries + 1}: Error parsing questions - {e}")
                retries += 1
                if retries == max_retries:
                    print("Max retries reached. Moving on without parsing questions.")
        return response.content, questions

    @classmethod
    async def ask_questions(cls, session: Session, questions: List[str]) -> List[str]:
        """Loop over the questions and ask honcho about them"""
        answers = []
        for question in questions:
            answer = session.chat(question)
            answers.append(answer)
        return answers

    @classmethod
    async def generate_response(cls, input: str, thought: str, answers: List[str], chat_history: List[str]) -> str:
        """Collate the answers to the questions and generate a response with those as context"""
        response_prompt = ChatPromptTemplate.from_messages([
            cls.system_response
        ])
        chain = response_prompt | cls.gpt_4
        response = await chain.ainvoke({
            "input": input,
            "thought": thought,
            "answers": answers,
            "chat_history": langchain_message_unpacker(chat_history)
        })
        return response.content



    @classmethod
    async def chat(
        cls, 
        input: str, 
        chat_history: List[str], 
        message: Message, 
        session: Session, 
    ) -> str:
        """Chat with the user"""

        urls = await cls.check_for_link(input)
        if urls:
            contents = await cls.get_webpage_content(urls)
            summaries = []
            if contents:  # Check if contents is not empty
                for content in contents:
                    # Ensure content is loaded correctly and has page_content attribute
                    summary = await cls.summarize_webpage_content(content[0].page_content)
                    summaries.append(summary)
                # Generate response based on summaries
                response = await cls.generate_response_urls(summaries, chat_history)
                return response

        # no links, let's continue the convo
        thought, questions = await cls.generate_thought(input, chat_history)
        session.create_metamessage(message, metamessage_type="thought", content=thought)  # write intermediate thought to honcho
        answers = await cls.ask_questions(session, questions)
        response = await cls.generate_response(input, thought, answers, chat_history)
        return response
    

