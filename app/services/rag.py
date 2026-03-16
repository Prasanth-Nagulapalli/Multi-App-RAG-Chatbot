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
from app.services.llm import get_llm, has_openai_key, get_llm_mode
from app.services.indexing import (
    index_exists,
    get_active_collection_name,
    release_vectordb,
    EMBED_MODEL,
)
from app.db import get_app

# Configuration
TOP_K = int(os.getenv("RAG_K", "6"))
FETCH_K = int(os.getenv("RAG_FETCH_K", "25"))
MMR_LAMBDA = float(os.getenv("RAG_MMR_LAMBDA", "0.5"))
SEARCH_TYPE = os.getenv("RAG_SEARCH_TYPE", "mmr")  # "mmr" or "similarity"
CHAIN_TYPE = os.getenv("RAG_CHAIN_TYPE", "refine")  # "refine" or "stuff"
ENABLE_MULTI_QUERY = os.getenv("RAG_MULTIQUERY", "0") == "1"


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

Answer (be direct and specific; use short bullets when helpful):""",
        input_variables=["context", "question"]
    )


def get_refine_prompt_template(app_id: str, app_name: str) -> PromptTemplate:
    """Prompt used for the 'refine' chain type."""
    return PromptTemplate(
        template=f"""You are a helpful assistant for the {app_name} system.
We are iteratively refining an answer using multiple context chunks from uploaded documents.

Question: {{question}}

Existing answer:
{{existing_answer}}

New context:
{{context}}

Instructions:
- If the new context adds useful details, update/improve the existing answer.
- If the new context is not relevant, keep the existing answer unchanged.
- If the question still cannot be answered from the contexts, say:
  "I don't have that information in the uploaded {app_id} documents."

Refined answer:""",
        input_variables=["question", "existing_answer", "context"],
    )


def load_vector_db(app_id: str):
    """Load the persisted Chroma vector DB for an app."""
    chroma_dir = get_chroma_dir(app_id)
    
    if not index_exists(app_id):
        raise ValueError(f"No index found for app '{app_id}'. Please train first.")
    
    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    collection_name = get_active_collection_name(app_id)
    vectordb = Chroma(
        persist_directory=chroma_dir,
        collection_name=collection_name,
        embedding_function=embedding
    )
    
    return vectordb


def _make_retriever(vectordb, llm):
    """
    Create a retriever with better recall.
    Defaults: MMR with fetch_k candidates -> k results.
    Optionally wraps with MultiQueryRetriever (OpenAI mode only).
    """
    search_type = SEARCH_TYPE if SEARCH_TYPE in ("mmr", "similarity") else "mmr"

    if search_type == "mmr":
        base = vectordb.as_retriever(
            search_type="mmr",
            search_kwargs={"fetch_k": FETCH_K, "k": TOP_K, "lambda_mult": MMR_LAMBDA},
        )
    else:
        base = vectordb.as_retriever(search_kwargs={"k": TOP_K})

    if has_openai_key() and ENABLE_MULTI_QUERY:
        try:
            from langchain.retrievers.multi_query import MultiQueryRetriever
            return MultiQueryRetriever.from_llm(retriever=base, llm=llm)
        except Exception as e:
            print(f"[WARN] MultiQueryRetriever disabled (import/init failed): {e}")

    return base


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
    
    vectordb = None
    try:
        # Load vector DB
        vectordb = load_vector_db(app_id)
        
        # Get LLM
        llm = get_llm()
        retriever = _make_retriever(vectordb, llm)
        print(
            f"[RAG] llm_mode={get_llm_mode()} "
            f"chain={CHAIN_TYPE} search={SEARCH_TYPE} k={TOP_K} fetch_k={FETCH_K} "
            f"multiquery={'on' if ENABLE_MULTI_QUERY else 'off'}"
        )
        
        # Create QA chain with custom prompt
        app_name = app.get("name", app_id)
        prompt = get_prompt_template(app_id, app_name)
        refine_prompt = get_refine_prompt_template(app_id, app_name)
        
        # Use RetrievalQA if we have OpenAI, otherwise do manual retrieval
        if has_openai_key():
            chain_type = CHAIN_TYPE if CHAIN_TYPE in ("refine", "stuff") else "stuff"
            try:
                if chain_type == "refine":
                    qa_chain = RetrievalQA.from_chain_type(
                        llm=llm,
                        retriever=retriever,
                        chain_type="refine",
                        return_source_documents=True,
                        chain_type_kwargs={
                            "question_prompt": prompt,
                            "refine_prompt": refine_prompt,
                        },
                    )
                else:
                    qa_chain = RetrievalQA.from_chain_type(
                        llm=llm,
                        retriever=retriever,
                        chain_type="stuff",
                        return_source_documents=True,
                        chain_type_kwargs={"prompt": prompt},
                    )

                result = qa_chain.invoke(message)
                answer = result["result"]
                source_docs = result.get("source_documents", [])
            except Exception as e:
                # Safe fallback (LangChain prompt keys can vary by version)
                print(f"[WARN] RetrievalQA chain failed (type={chain_type}); falling back to stuff. Error: {e}")
                qa_chain = RetrievalQA.from_chain_type(
                    llm=llm,
                    retriever=retriever,
                    chain_type="stuff",
                    return_source_documents=True,
                    chain_type_kwargs={"prompt": prompt},
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
    finally:
        # Ensure no lingering file locks (Windows) after retrieval.
        release_vectordb(vectordb)

