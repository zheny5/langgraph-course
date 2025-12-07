# from langchain import hub
from langsmith import Client
from langchain_core.output_parsers import StrOutputParser
# from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek

# llm = ChatOpenAI(temperature=0)
llm = ChatDeepSeek(model="deepseek-chat")
client = Client()
prompt = client.pull_prompt("rlm/rag-prompt")
# prompt = hub.pull("rlm/rag-prompt")

generation_chain = prompt | llm | StrOutputParser()
