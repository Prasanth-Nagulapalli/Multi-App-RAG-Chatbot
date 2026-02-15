"""
RAG (Retrieval-Augmented Generation) service.
Handles chat logic, vector DB loading, and retrieval.
"""
import os
from typing import Dict, Any, List, Optional

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

from app.services.storage import get_chroma_dir
from app.services.llm import get_llm, has_openai_key
from app.services.indexing import index_exists, EMBED_MODEL
from app.db import get_app

# Configuration
TOP_K = 3
SIMILARITY_THRESHOLD = 0.3  # Minimum similarity score


# Custom prompt template for app-specific answers
def get_prompt_template(app_id: str, app_name: str) -> PromptTemplate:
    return PromptTemplate(
        template=f"""You are a helpful assistant for the {app_name} system.
Answer the question based ONLY on the following context from the uploaded documents.
If the question cannot be answered from the context, say:
"I don't have that information in the uploaded {app_id} documents."

Context:
{{context}}

Question: {{question}}

Answer:""",
        input_variables=["context", "question"]
    )


def load_vector_db(app_id: str):
    """Load the persisted Chroma vector DB for an app."""
    chroma_dir = get_chroma_dir(app_id)
    
    if not index_exists(app_id):
        raise ValueError(f"No index found for app '{app_id}'. Please train first.")
    
    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    vectordb = Chroma(
        persist_directory=chroma_dir,
        embedding_function=embedding
    )
    
    return vectordb


def chat(app_id: str, message: str) -> Dict[str, Any]:
    """
    Process a chat message using RAG.
    Returns answer and source documents.
    """
    print(f"\n[CHAT] Chat request for app: {app_id}")
    print(f"   Message: {message[:100]}...")
    
    # Validate app exists
    app = get_app(app_id)
    if not app:
        return {
            "success": False,
            "error": f"App '{app_id}' not found",
            "answer": None,
            "sources": []
        }
    
    # Check if trained
    if app["status"] != "READY":
        return {
            "success": False,
            "error": f"App '{app_id}' is not trained yet. Status: {app['status']}",
            "answer": None,
            "sources": []
        }
    
    try:
        # Load vector DB
        vectordb = load_vector_db(app_id)
        
        # Create retriever
        retriever = vectordb.as_retriever(search_kwargs={"k": TOP_K})
        
        # Get LLM
        llm = get_llm()
        
        # Create QA chain with custom prompt
        app_name = app.get("name", app_id)
        prompt = get_prompt_template(app_id, app_name)
        
        # Use RetrievalQA if we have OpenAI, otherwise do manual retrieval
        if has_openai_key():
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt}
            )
            
            result = qa_chain.invoke(message)
            answer = result["result"]
            source_docs = result.get("source_documents", [])
        else:
            # Manual retrieval for mock LLM
            docs = retriever.invoke(message)
            
            if not docs:
                answer = f"I don't have that information in the uploaded {app_id} documents."
                source_docs = []
            else:
                # Construct context
                context = "\n\n".join([doc.page_content for doc in docs])
                full_prompt = prompt.format(context=context, question=message)
                answer = llm.generate(full_prompt)
                source_docs = docs
        
        # Extract source filenames
        sources = []
        for doc in source_docs:
            source = doc.metadata.get("source", "unknown")
            filename = os.path.basename(source)
            if filename not in sources:
                sources.append(filename)
        
        print(f"   [OK] Answer generated. Sources: {sources}")
        
        return {
            "success": True,
            "answer": answer,
            "sources": sources,
            "error": None
        }
        
    except Exception as e:
        print(f"   [ERR] Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "answer": None,
            "sources": []
        }

