# Hybrid Local RAG Agent

## Overview
This is a portfolio-grade AI tool designed to run entirely offline. It leverages the power of local LLMs (Google Gemma 3 and Qwen 2.5) to provide a secure and private RAG (Retrieval-Augmented Generation) experience.

## Features
- **Offline Capability**: Runs locally on your machine without needing an internet connection for inference.
- **Multi-Model Support**: Switch seamlessly between `gemma3:270m` and `qwen2.5:0.5b`.
- **Versatile File Ingestion**: Supports PDF, DOCX, TXT, CSV, Excel, and PowerPoint files.
- **Dual Interface**:
  - **Web Control Panel**: Built with Streamlit for easy file management and model configuration.
  - **Terminal Chat**: A distraction-free command-line interface for interacting with your documents.

## Tech Stack
- **LangChain**: For orchestration and RAG flows.
- **ChromaDB**: For vector storage and retrieval.
- **Ollama**: For running local LLMs.
- **Streamlit**: For the control panel UI.

## Getting Started

1. **Prerequisites**: Ensure you have [Ollama](https://ollama.com/) installed.
2. **Installation**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the App**:
   ```bash
   python start_app.py
   ```

## Usage
1. Open the Control Panel (automatically launches in your browser).
2. Upload your documents.
3. Click "Process Files" to ingest them into the local vector database.
4. Switch to the terminal window to chat with your documents.
