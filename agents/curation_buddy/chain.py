import os, re
from typing import List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, load_prompt
from langchain_core.output_parsers import NumberedListOutputParser
from langchain_core.messages import HumanMessage

from honcho import Collection, Session, Message


# takes user input
#  quick check if it contains a link
#  if it does, get the webpage content and extract the topic. ask a follow up that prods at why they might be interested in it
#  while we feel like we haven't gotten to the bottom of the user's interest, keep engaging with them about it
# generate a thought about the user's needs, list of questions that'd help it know
# parse out those questions, loop over the endpoint asking Honcho about them
# collate those answers, generate a response with those as context

class CurationBuddyChain:
    """Chain for executing the curation buddy logic"""
    # prompts
    # lm


    def __init__(self) -> None:
        pass

    @classmethod
    async def check_for_link(cls, input: str) -> List[str]:
        url_pattern = re.compile(r'\b((http|https):\/\/?)[^\s()<>]+(?:\([\w\d]+\)|([^[:punct:]\s]|\/?))')
        urls = re.findall(url_pattern, input)
        return urls
    
    @classmethod
    async def get_webpage_content(cls, link: str) -> List[str]:
        pass

    @classmethod
    async def generate_thought(cls, input: str) -> str:
        """Generate a thought about the user's input along with a list of questions that'd help it better serve the user"""
        pass

    @classmethod
    async def ask_questions(cls, questions: List[str]) -> List[str]:
        """Loop over the questions and ask honcho about them"""
        pass

    @classmethod
    async def generate_response(cls, input: str, questions: List[str]) -> str:
        """Collate the answers to the questions and generate a response with those as context"""
        pass

    

