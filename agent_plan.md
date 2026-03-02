# Agent Execution Plan: Document Ingestion & Vector Embedding Pipeline

## 1. Project Overview
You are tasked with building a production-ready Python module that processes documents (PDF and DOCX), splits the extracted text into chunks, generates vector embeddings using the Google Gemini API, and stores the results in a PostgreSQL database.

The final deliverable must be highly modular, robust, and formatted to impress senior engineers reviewing this as a job assignment. All Python code MUST be strictly contained within a single file (`index_documents.py`).

## 2. Engineering Standards & Architecture
To ensure industry-level quality, adhere strictly to the following standards:
* **Single File Architecture:** All logic must reside within `index_documents.py`. Do not create multiple Python files. Use internal classes or functions (e.g., `DocumentProcessor`, `GeminiEmbedder`, `DatabaseManager`) to maintain separation of concerns within the single script.
* **Professional Logging:** Use Python's built-in `logging` module for all terminal output (INFO, WARNING, ERROR levels). Do not use plain `print()` statements. The code must provide a clear, timestamped execution trace so the reviewer knows exactly what is happening at each step (e.g., "[INFO] Extracted 4,520 characters... [INFO] Created 42 chunks...").
* **Security:** **NEVER** hardcode API keys or database connection strings. Use a `.env` file via the `python-dotenv` library.
* **Error Handling:** Implement `try-except` blocks for file reading, API rate limits/failures, and database connections. Log all errors appropriately.
* **Database:** We are using **PostgreSQL via Docker** locally. The database MUST have the `pgvector` extension enabled to store embeddings.

## 3. Database Strategy (Docker & pgvector)
We will use a local Docker container for the database to ensure a standardized environment. 

**Required Table Schema:**
* `id`: Unique identifier (UUID or Auto-increment Primary Key).
* `chunk_text`: The extracted text segment (Text).
* `embedding`: The vector embedding (Vector type, dimension depends on Gemini model).
* `filename`: Name of the source file (Varchar).
* `strategy_split`: The chunking strategy used (Varchar).
* `at_created`: Timestamp of insertion (Timestamp, default to current time).

*Agent Instruction:* Ensure the Python code executes `CREATE EXTENSION IF NOT EXISTS vector;` before attempting to create the table.

## 4. Pipeline Requirements

### A. Input & Extraction
* Accept `.pdf` or `.docx` files.
* Extract clean text, stripping out unnecessary metadata or messy formatting. Log the successful extraction and character count.

### B. Chunking Strategies
Implement a router/selector that allows the user to choose one of three splitting strategies:
1. **Fixed-size with overlap:** e.g., 1000 characters per chunk, 200 characters overlap.
2. **Sentence-based splitting:** Split cleanly at sentence boundaries (using basic regex).
3. **Paragraph-based splitting:** Split by double newlines (`\n\n`).
*Log the chosen strategy and the final number of chunks created.*

### C. Embedding Generation
* Use the official `google-genai` SDK.
* Model: `gemini-embedding-001`
*Log the success or failure of the API calls.*

## 5. Files to Generate

Please generate the following files to complete this project:

### File 1: `docker-compose.yml`
Create a Docker Compose file using the `pgvector/pgvector:pg16` image. Expose port 5432 and set default environment variables (user, password, db name).

### File 2: `.env.example`
Provide a template for the environment variables:
    GEMINI_API_KEY=your_gemini_api_key_here
    POSTGRES_URL=postgresql://user:password@localhost:5432/vector_db

### File 3: `requirements.txt`
Include the following dependencies (with appropriate versions):
    google-genai
    psycopg2-binary
    pgvector
    python-dotenv
    pypdf
    python-docx

### File 4: `index_documents.py`
The main and **only** executable Python script. It should use `argparse` to accept the file path and chunking strategy from the command line, orchestrate the entire pipeline, and heavily utilize the `logging` module to report progress to the console. It MUST use the new SDK syntax: `from google import genai` and instantiate the client using `client = genai.Client()`. Do not use the deprecated GenerativeModel legacy patterns. 

### File 5: `README.md`
Generate a comprehensive, professional README.md that includes:
* **Project Title & Description**
* **Prerequisites:** Mention Python 3.9+ and optionally Docker.
* **Database Setup (Two Options):**
    * **Option A (Recommended):** Use the provided `docker-compose.yml` to spin up a local PostgreSQL instance with `pgvector` pre-installed (explain how to run `docker compose up -d`).
    * **Option B (Existing DB):** Use an existing PostgreSQL database (local or cloud-based). Explicitly note that the database environment must support the `pgvector` extension, and running `CREATE EXTENSION IF NOT EXISTS vector;` is required (which the script will attempt to execute automatically).
* **Environment Setup:** Explain how to create the `.env` file from `.env.example` and set the `POSTGRES_URL` based on the chosen database option.
* **Installation:** How to install dependencies from `requirements.txt`.
* **Usage Examples:** Clear terminal commands showing how to run `index_documents.py` with arguments for different files and chunking strategies.
* **Architecture Note:** A brief explanation of the internal modular code structure (using classes/functions within the single script), the `logging` setup, and the use of `pgvector`.