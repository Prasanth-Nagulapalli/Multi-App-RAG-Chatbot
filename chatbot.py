# import os
# from dotenv import load_dotenv
# from langchain_community.chat_models import ChatOpenAI
# from langchain_community.document_loaders import TextLoader
# from langchain_community.vectorstores import Chroma
# from langchain_community.embeddings import OpenAIEmbeddings
# from langchain.chains import RetrievalQA

# # Load API key
# load_dotenv()
# openai_key = os.getenv("OPENAI_API_KEY")

# # Load and embed documents
# loader = TextLoader("data/css_docs.txt", encoding="utf-8")
# docs = loader.load()

# embedding = OpenAIEmbeddings(model="text-embedding-3-small")

# vectordb = Chroma.from_documents(docs, embedding)

# # Set up retrieval-based QA chain
# qa_chain = RetrievalQA.from_chain_type(
#     llm=ChatOpenAI(model_name="gpt-4", temperature=0),
#     retriever=vectordb.as_retriever(search_kwargs={"k": 3}),
#     return_source_documents=True
# )

# # Chat loop
# print("Ask me anything about the CSS system (type 'exit' to quit):")
# while True:
#     query = input("You: ")
#     if query.lower() == 'exit':
#         break

#     result = qa_chain(query)
#     print("\nCSS Bot:", result["result"])



import os
from dotenv import load_dotenv

# ⬇️ modern import paths (no deprecation warnings)
from langchain_community.chat_models import ChatOpenAI
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import DirectoryLoader



from langchain.chains import RetrievalQA

# 1️⃣  Load API key
load_dotenv()          # reads .env
openai_key = os.getenv("OPENAI_API_KEY")

# 2️⃣  Load CSS docs
# loader = TextLoader("data/css_docs.txt", encoding="utf-8")
loader = DirectoryLoader("data", glob="css_docs*.txt",
                         loader_cls=TextLoader,
                         loader_kwargs={"encoding": "utf-8"})
docs = loader.load()

# 3️⃣  Create embeddings (cheap model)
embedding = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# 4️⃣  Build vector store
vectordb = Chroma.from_documents(docs, embedding)

# 5️⃣  Retrieval-augmented QA chain with GPT-3.5
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0),
    retriever=vectordb.as_retriever(search_kwargs={"k": 3}),
    return_source_documents=True
)

# 6️⃣  Simple CLI loop
print("Ask me anything about the CSS system (type 'exit' to quit):")
while True:
    q = input("You: ")
    if q.lower() == "exit":
        break
    result = qa_chain(q)
    print("CSS Bot:", result["result"], "\n")
