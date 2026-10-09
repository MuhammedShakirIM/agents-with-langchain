from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_xai import ChatXAI

from learning_companion.config import settings

LEARNING_COMPANION_INSTRUCTION = (
    "You are a friendly Learning Companion. "
    "Explain ideas simply, check understanding, and encourage the learner."
)


def build_chain():
    """Prompt → Grok → text. Built per request so a missing key never blocks startup."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", LEARNING_COMPANION_INSTRUCTION),
            ("human", "{question}"),
        ]
    )
    model = ChatXAI(
        model=settings.grok_model_name,
        api_key=settings.grok_api_key,
        xai_api_base=settings.grok_api_base_url,
    )
    return prompt | model | StrOutputParser()
