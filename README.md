# RAG Support Client

A powerful Retrieval-Augmented Generation (RAG) support client that provides context-aware responses from Markdown documentation. Built with LangChain, Ollama, and ChromaDB, featuring both a Streamlit UI and FastAPI backend.

![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- 🔍 Smart document retrieval using RAG technology
- 🤖 Local LLM integration with Ollama
- 💾 Efficient vector storage with ChromaDB
- 🌐 Dual interface: Streamlit UI and FastAPI backend
- 📝 Markdown documentation processing
- 🔄 Real-time conversation context management
- 🎯 High-precision response generation
- 📊 Administrative interface for document management

## Quick Start

1. **Prerequisites**
   - Python 3.11 or higher
   - [Ollama](https://ollama.ai/) installed and running
   - [ChromaDB](https://www.trychroma.com/) prerequisites

2. **Installation**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
   pip install -e '.[dev]'

3. **Configuration**

    ```bash
    #Edit .env file with your settings
    cp .env.example .env
    ```

4. **Run the Application**

    ```bash
    # Start the FastAPI server
    python main.py

    # Start the Streamlit UI (in a new terminal)
    streamlit run streamlit_app.py
    ```

5. **Documentation**
    User Quick Start Guide
    Development Guide
    Technical Documentation

6. **Architecture**
    The application follows a modular architecture with these key components:

    RAG Chain: Central component handling document retrieval and response generation
    Document Processing: Intelligent Markdown processing with metadata extraction
    Vector Store: ChromaDB-based similarity search
    LLM Integration: Local deployment using Ollama
    Dual Interface: FastAPI backend for remote API client as a ChatBot and a Streamlit UI for local testing

7. **Contributing**
    Contributions are welcome! Please read our Contributing Guidelines before submitting pull requests.

8. **License**
    This project is licensed under the MIT License - see the LICENSE file for details.
