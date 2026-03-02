# Document Ingestion & Vector Pipeline

This repository contains a Python module (`index_documents.py`) built to ingest PDF and DOCX files, extract text, split the content into manageable chunks, generate vector embeddings using the Google Gemini API, and store the resulting data in a PostgreSQL database (equipped with the `pgvector` extension).

## Prerequisites
- Python 3.9+ 
- Docker and Docker Compose (Optional, but recommended for local database setup)

## Database Setup

This project requires a PostgreSQL database with the **pgvector** extension installed. You have two options for setting this up:

### Option A: Local Docker Setup (Recommended)
You can quickly spin up a pre-configured PostgreSQL instance using the provided `docker-compose.yml` file.

1. Ensure Docker Desktop (or equivalent) is running.
2. In the terminal, navigate to the project directory and run:
   ```bash
   docker-compose up -d
   ```
This will start the database in the background on `localhost:5432`.

### Option B: Existing Database
If you prefer to use an existing database (local or cloud-based), ensure the PostgreSQL instance supports the `pgvector` extension. The Python script will automatically attempt to execute `CREATE EXTENSION IF NOT EXISTS vector;` upon its first connection.

## Environment Variables Configuration

Ensure you create a `.env` file in the root of the project with the following two keys:

- `GEMINI_API_KEY`: Your valid Google Gemini API key.
- `POSTGRES_URL`: The connection string to your database (e.g., `postgresql://myuser:mypassword@localhost:5432/vector_db` if using the Docker setup).

## Installation

**Option 1: Using `uv` (Recommended - Blazing Fast)**
If you have [uv](https://github.com/astral-sh/uv) installed, you can create the environment and install dependencies in seconds:
```bash
uv venv --python 3.12
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
uv pip install -r requirements.txt
```

**Option 2: Using standard `pip`**
If you don't have `uv`, standard pip works perfectly:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Run the main script from the command line, providing the path to the document you wish to process.

**Basic Execution (Defaults to Paragraph-based Splitting):**
```bash
python index_documents.py "path/to/your/document.pdf"
```

> **Note:** Every time you run the command above, the script will automatically clear the existing `document_chunks` database table and insert only the new data from the document you just processed. It does not accumulate documents!

**Specifying a Chunking Strategy:**
You can optionally define how the text should be split using the `--strategy` flag. The available options are `fixed`, `sentence`, or `paragraph`.

```bash
# Split into fixed-size chunks (1000 chars with 200 char overlap)
python index_documents.py "path/to/your/document.docx" --strategy fixed

# Split by sentences
python index_documents.py "path/to/your/document.pdf" --strategy sentence
```

## Architecture Notes
To adhere to the assignment requirements, the entire ingestion logic is strictly contained within `index_documents.py`. Internally, the script leverages a highly modular function-based architecture:
- Data extraction (`pypdf` / `python-docx`)
- Router-pattern text chunking (Fixed, Sentence, Paragraph)
- Vectorization (`google-genai`)
- Data persistence (`psycopg2` + `pgvector`) 

Extensive logging is utilized via Python’s built-in `logging` module to provide a clear execution trace for debugging and verification purposes.
