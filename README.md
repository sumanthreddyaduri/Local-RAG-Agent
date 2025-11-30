# 🧠 Hybrid Local RAG Agent

![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20UI-black?logo=flask&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-white?logo=ollama&logoColor=black)
![LangChain](https://img.shields.io/badge/LangChain-RAG-green?logo=langchain&logoColor=white)

## 🚀 Overview
**Hybrid Local RAG Agent** is a privacy-first, offline AI tool designed for secure document analysis. It leverages local Large Language Models (LLMs) via **Ollama** to ingest, index, and chat with your documents (PDF, DOCX, TXT, etc.) without a single byte leaving your machine.

> **Why I Built This:**  
> I wanted to solve the privacy concerns associated with cloud-based AI. By running everything locally, I ensure that sensitive documents never leave the machine. This project demonstrates the integration of modern LLMs (Gemma 3, Qwen 2.5) with robust software engineering patterns (Flask, FAISS, LangChain) in a bleeding-edge Python 3.14 environment.

## 🏗️ Architecture

```mermaid
graph TD
    User[User] -->|Uploads Docs| UI[Flask Web UI]
    User -->|Chats| Terminal[Terminal Interface]
    UI -->|Ingests| Backend[Backend Logic]
    Backend -->|Chunks & Embeds| FAISS[FAISS Vector DB]
    Terminal -->|Queries| FAISS
    Terminal -->|Retrieves Context| LLM[Ollama (Gemma/Qwen)]
    LLM -->|Response| Terminal
```

## ✨ Features
- **🔒 100% Offline & Private**: No API keys, no cloud costs, no data leaks.
- **🧠 Multi-Model Brain**: Switch instantly between `gemma3:270m` (speed) and `qwen2.5:0.5b` (reasoning).
- **📂 Universal Ingestion**: Supports PDF, DOCX, TXT, CSV, Excel, and PowerPoint.
- **🖥️ Dual Interface**:
  - **Web Control Panel**: A sleek Flask-based UI for managing your "Knowledge Base" and configuring the agent.
  - **Terminal Chat**: A distraction-free, hacker-style command line interface for deep work.
- **🔄 Dynamic Context**: The agent knows exactly which files it has read and cites them.

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sumanthreddyaduri/Local-RAG-Agent.git
   cd Local-RAG-Agent
   ```

2. **Create a Virtual Environment** (Recommended):
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Ollama**:
   - Download from [ollama.com](https://ollama.com).
   - Pull the required models:
     ```bash
     ollama pull gemma3:270m
     ollama pull qwen2.5:0.5b
     ollama pull nomic-embed-text
     ```

## 🚀 Usage

Run the application with a single command:
```bash
python start_app.py
```
- **Web UI**: Automatically opens at `http://localhost:8501`. Use this to upload files and switch models.
- **Terminal**: The chat interface will appear in your console. Start typing to talk to your documents!

## 🛠️ Tech Stack
- **LangChain**: Orchestration and RAG chains.
- **FAISS**: High-performance local vector storage.
- **Flask**: Lightweight web server for the UI.
- **Ollama**: Local LLM runner.
