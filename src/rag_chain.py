from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA

from src.config import CHROMA_DIR, EMBED_MODEL, CHAT_MODEL, TOP_K, OPENAI_API_KEY

def create_qa_chain():
    # 1) Load persisted vector DB (fast)
    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    vectordb = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embedding
    )

    # 2) Retriever: how many chunks to fetch
    retriever = vectordb.as_retriever(search_kwargs={"k": TOP_K})

    # 3) LLM
    llm = ChatOpenAI(
        model_name=CHAT_MODEL,
        temperature=0,
        openai_api_key=OPENAI_API_KEY
    )

    # 4) RetrievalQA chain (no custom prompt - GPT uses context naturally)
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True
    )
