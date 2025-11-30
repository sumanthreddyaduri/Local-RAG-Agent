import json
import os
import time
import sys
from backend import get_rag_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

def main():
    print("\n" + "="*40)
    print("🤖 TERMINAL AGENT ONLINE")
    print("👉 Control settings via the Web Window")
    print("="*40)

    current_model = None

    while True:
        try:
            # Load latest config
            with open("config.json", "r") as f: 
                new_model = json.load(f)["model"]
            
            if current_model is None:
                current_model = new_model
            elif new_model != current_model:
                msg = ""
                if "gemma" in new_model.lower():
                    msg = "Your next response will be replied by Gemma"
                elif "qwen" in new_model.lower():
                    msg = "Your next response will be replied by Qwen"
                else:
                    msg = f"Switched to {new_model}"
                
                # Print message, wait, then clear
                sys.stdout.write(f"\n{msg}")
                sys.stdout.flush()
                time.sleep(5)
                # Clear the line
                sys.stdout.write(f"\r{' ' * (len(msg) + 10)}\r")
                sys.stdout.flush()
                
                current_model = new_model
            
            query = input(f"\nAgent >> ")
            if query.lower() in ["exit", "quit"]: break
            if not query.strip(): continue

            # Build Chain
            retriever, llm = get_rag_chain(current_model)
            
            def format_docs(docs):
                return "\n\n".join(f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}" for doc in docs)

            if retriever is None:
                # Fallback to simple chat if no documents indexed
                template = "Answer the question:\nQuestion: {question}"
                chain = (
                    {"question": RunnablePassthrough()} 
                    | ChatPromptTemplate.from_template(template) 
                    | llm 
                    | StrOutputParser()
                )
            else:
                template = """You are an AI assistant with access to the following documents. 
The context below contains the content of the documents and their source filenames.
Answer the question based strictly on the context provided. 
If the user asks what files you have, list the unique 'Source' filenames found in the context.

Context:
{context}

Question: {question}"""
                chain = (
                    {"context": retriever | format_docs, "question": RunnablePassthrough()} 
                    | ChatPromptTemplate.from_template(template) 
                    | llm 
                    | StrOutputParser()
                )
            
            # Stream Answer
            print("\n", end="")
            for chunk in chain.stream(query):
                print(chunk, end="", flush=True)
            print("\n")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
