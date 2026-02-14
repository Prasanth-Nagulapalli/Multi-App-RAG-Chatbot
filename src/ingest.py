from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from src.config import DATA_DIR, CHROMA_DIR, EMBED_MODEL

def build_index():
    # 1) Load all css docs
    loader = DirectoryLoader(
        DATA_DIR,
        glob="css_docs*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    docs = loader.load()

    # 2) Chunk documents into smaller pieces
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120
    )
    chunks = splitter.split_documents(docs)

    # 3) Create embeddings
    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    # 4) Persist vector DB to disk (enterprise pattern)
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        persist_directory=CHROMA_DIR
    )

    vectordb.persist()
    print(f"✅ Index built and saved to: {CHROMA_DIR}")
    print(f"Docs: {len(docs)} | Chunks: {len(chunks)}")

if __name__ == "__main__":
    build_index()
