"""
Enhanced CLI Chat Interface with persistent history and improved UX.
"""

import json
import os
import time
import sys
from backend import get_rag_chain
from config_manager import load_config
from database import (
    get_or_create_default_session, add_message, 
    format_history_for_prompt, create_session,
    get_recent_messages, get_new_messages # Added imports
)

from health_check import check_ollama_health
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


def print_header():
    """Print the CLI header."""
    print("\n" + "=" * 50)
    print("   🤖 RAG AGENT - Terminal Interface")
    print("   Control settings via the Web UI at localhost:8501")
    print("=" * 50)


def print_status(config):
    """Print current status."""
    print(f"\n📊 Status:")
    print(f"   Model: {config.get('model', 'unknown')}")
    print(f"   Hybrid Search: {'Enabled' if config.get('use_hybrid_search') else 'Disabled'}")
    print(f"   History Context: {config.get('max_history_context', 10)} messages")
    print()


def check_ollama():
    """Check if Ollama is available."""
    config = load_config()
    health = check_ollama_health(config.get('ollama_host', 'http://localhost:11434'))
    
    if not health['available']:
        print(f"\n⚠️  Warning: Ollama is not available!")
        print(f"   Error: {health['error']}")
        print(f"   Please start Ollama and try again.\n")
        return False
    
    print(f"\n✅ Ollama connected ({health['response_time_ms']}ms)")
    if health['models']:
        print(f"   Available models: {', '.join(health['models'][:5])}")
    return True


def format_docs(docs):
    """Format retrieved documents."""
    return "\n\n".join(
        f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}" 
        for doc in docs
    )


def main():
    print_header()
    
    # Check Ollama connection
    if not check_ollama():
        print("Waiting for Ollama to become available...")
        while not check_ollama():
            time.sleep(5)
    
    config = load_config()
    print_status(config)
    
    # Get or create a CLI session
    session_id = get_or_create_default_session()
    current_model = config.get("model", "gemma3:270m")
    last_mode = "cli"
    
    # Initialize Last Message ID
    initial_msgs = get_recent_messages(session_id, 1)
    last_message_id = initial_msgs[-1]['id'] if initial_msgs else 0

    # Window Management Helper
    def set_window_visibility(visible):
        if sys.platform != 'win32':
            return
        import ctypes
        from ctypes import wintypes
        
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
        
        target_hwnd = None
        
        def foreach_window(hwnd, lParam):
            nonlocal target_hwnd
            if not IsWindowVisible(hwnd): return True
            length = GetWindowTextLength(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buff, length + 1)
            title = buff.value
            if "onyx cli" in title.lower():
                target_hwnd = hwnd
                return False 
            return True
            
        console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if console_hwnd and IsWindowVisible(console_hwnd):
             length = GetWindowTextLength(console_hwnd)
             buff = ctypes.create_unicode_buffer(length + 1)
             GetWindowText(console_hwnd, buff, length + 1)
             if "onyx" in buff.value.lower():
                 target_hwnd = console_hwnd
        
        if not target_hwnd:
            ctypes.windll.user32.EnumWindows(EnumWindowsProc(foreach_window), 0)
            
        if target_hwnd:
            cmd = 0 if not visible else 9 
            ctypes.windll.user32.ShowWindow(target_hwnd, cmd)

    print("Type 'help' for commands, 'exit' to quit.\n")
    
    history_text = format_history_for_prompt(session_id, 10) 
    last_poll_time = time.time()

    while True:
        try:
            config = load_config()
            new_model = config.get("model", "gemma3:270m")
            mode = config.get("mode", "cli")
            max_history = config.get("max_history_context", 10)
            
            if mode == "browser":
                if last_mode != "browser":
                    print("\n⏸️  [Browser Mode Active - CLI Chat Hidden]")
                    last_mode = "browser"
                    set_window_visibility(False)
                time.sleep(1)
                continue
            elif mode == "cli" and last_mode == "browser":
                set_window_visibility(True)
                print("\n▶️  [CLI Mode Reactivated]")
                history_text = format_history_for_prompt(session_id, max_history)
                recents = get_recent_messages(session_id, 1)
                if recents: last_message_id = recents[-1]['id']
                last_mode = "cli"
                print("\n🤖 Agent >> ", end="", flush=True)

            if new_model != current_model:
                model_name = new_model.split(':')[0].title()
                print(f"\n🔄 Model switched to {model_name}")
                current_model = new_model
            
            try:
                line = ""  # Ensure line is initialized
                if sys.platform == 'win32':
                    import msvcrt
                    sys.stdout.write("\r🤖 Agent >> " + line)
                    sys.stdout.flush()
                    
                    while True:
                        if msvcrt.kbhit():
                            ch = msvcrt.getwche()
                            if ch == '\r' or ch == '\n':
                                print()
                                break
                            elif ch == '\b':
                                if len(line) > 0:
                                    line = line[:-1]
                                    sys.stdout.write(' \b')
                            elif ch == '\x03':
                                raise KeyboardInterrupt
                            else:
                                line += ch
                        else:
                            time.sleep(0.1)
                            
                            if time.time() - last_poll_time > 2.0:
                                last_poll_time = time.time()
                                try:
                                    # Use a separate session/connection-safe call if needed
                                    new_msgs = get_new_messages(session_id, last_message_id)
                                    if new_msgs:
                                        sys.stdout.write('\r' + ' ' * (len(line) + 20) + '\r')
                                        for msg in new_msgs:
                                            if msg['id'] > last_message_id:
                                                last_message_id = msg['id']
                                                role = "User" if msg['role'] == 'user' else "Assistant"
                                                print(f"\n{role}: {msg['content']}")
                                        
                                        sys.stdout.write("\n🤖 Agent >> " + line)
                                        sys.stdout.flush()
                                        history_text = format_history_for_prompt(session_id, max_history)
                                except Exception:
                                    pass

                            temp_config = load_config()
                            if temp_config.get("mode") == "browser":
                                break
                    
                    if config.get("mode") == "browser":
                        continue
                    query = line.strip()
                else:
                    query = input("\n🤖 Agent >> ").strip()
                    
            except EOFError:
                break
            
            if not query: continue
            
            query_lower = query.lower()
            if query_lower in ["exit", "quit", "q"]:
                print("\n👋 Goodbye!")
                break
            
            if query_lower == "help":
                print("\n📖 Commands:")
                print("   help     - Show this help")
                print("   status   - Show current settings")
                print("   new      - Start a new chat session")
                print("   clear    - Clear current session history")
                print("   exit/q   - Exit the CLI")
                print()
                continue
            
            if query_lower == "status":
                config = load_config()
                print_status(config)
                continue
            
            if query_lower == "new":
                session_id = create_session("CLI Session")
                print("\n✨ New chat session started!")
                # Reset last_message_id for new session
                last_message_id = 0 
                continue
            
            if query_lower == "clear":
                from database import clear_session_messages
                clear_session_messages(session_id)
                print("\n🗑️  Chat history cleared!")
                # Reset last_message_id after clearing
                last_message_id = 0
                continue

            # Build and execute the RAG chain
            retriever, llm = get_rag_chain(current_model)
            
            # Get history from database
            history_text = format_history_for_prompt(session_id, max_history)

            if retriever is None:
                template = """You are a helpful AI assistant. Answer the question based on the conversation history.

Conversation History:
{history}

User Question: {question}

Provide a helpful and informative response."""
                chain = (
                    {"question": RunnablePassthrough(), "history": lambda x: history_text} 
                    | ChatPromptTemplate.from_template(template) 
                    | llm 
                    | StrOutputParser()
                )
            else:
                template = """You are an AI assistant with access to the user's documents. 
The context below contains relevant excerpts from the documents along with their source filenames.
Answer the question based on the context provided and the conversation history.
If the user asks what files or documents you have access to, list the unique source filenames from the context.
If you cannot find the answer in the context, say so clearly.

Conversation History:
{history}

Document Context:
{context}

User Question: {question}

Provide a helpful response based on the documents."""

                def get_context(q):
                    docs = retriever.invoke(q) if hasattr(retriever, 'invoke') else retriever.get_relevant_documents(q)
                    return format_docs(docs)

                chain = (
                    {"context": lambda x: get_context(x), "question": RunnablePassthrough(), "history": lambda x: history_text} 
                    | ChatPromptTemplate.from_template(template) 
                    | llm 
                    | StrOutputParser()
                )
            
            # Stream the response
            print("\n💭 ", end="", flush=True)
            full_response = ""
            
            try:
                for chunk in chain.stream(query):
                    print(chunk, end="", flush=True)
                    full_response += chunk
                print("\n")
                
                # Save to database
                add_message(session_id, 'user', query)
                add_message(session_id, 'assistant', full_response)
                
                # Update last_message_id after adding our own messages
                # This prevents us from re-printing our own messages if polling happens instantly
                recents = get_recent_messages(session_id, 1)
                if recents: last_message_id = recents[-1]['id']
                
            except Exception as e:
                print(f"\n\n❌ Error generating response: {e}")
                print("   Check if Ollama is running and the model is available.\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
