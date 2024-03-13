from typing import List
from langchain_core.messages import AIMessage, HumanMessage


def langchain_message_converter(messages: List):
    new_messages = []
    for message in messages:
        if message.is_user:
            new_messages.append(HumanMessage(content=message.content))
        else:
            new_messages.append(AIMessage(content=message.content))
    return new_messages

def langchain_message_unpacker(chat_history: List):
    unpacked_messages = [("user: " + message.content if isinstance(message, HumanMessage) else "ai: " + message.content) for message in chat_history]
    return "\n".join(unpacked_messages)

