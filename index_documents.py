import argparse
import logging
import os
import re
from pathlib import Path
from typing import List, Tuple, Optional

from google import genai
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extensions import connection as pg_conn
from pypdf import PdfReader
from docx import Document
from dotenv import load_dotenv

# ==============================================================================
# Setup & Configuration
# ==============================================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # Check standard naming or specific env variable 
POSTGRES_URL = os.getenv("POSTGRES_URL")
EMBEDDING_MODEL = "gemini-embedding-001"

client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables. Embedding will fail.")

if not POSTGRES_URL:
    logger.warning("POSTGRES_URL not found in environment variables. Database operations will fail.")


# ==============================================================================
# Document Extraction
# ==============================================================================

def extract_text(file_path: str) -> str:
    """Extracts raw text from a PDF or DOCX file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text = ""
    ext = path.suffix.lower()

    try:
        if ext == ".pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        elif ext == ".docx":
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            raise ValueError(f"Unsupported file format: {ext}. Must be .pdf or .docx")
            
        # Basic cleanup: remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        logger.info(f"Successfully extracted {len(text)} characters from {path.name}")
        return text

    except Exception as e:
        logger.error(f"Failed to extract text from {file_path}: {e}")
        raise


# ==============================================================================
# Chunking Strategies
# ==============================================================================

def chunk_fixed_size(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Splits text into fixed-size chunks with overlap."""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
        
    return chunks

def chunk_sentences(text: str) -> List[str]:
    """Splits text into chunks based on sentence boundaries."""
    # Basic regex for sentence splitting (handles '.', '!', '?')
    # Note: This is an approximation and might split on abbreviations
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def chunk_paragraphs(text: str) -> List[str]:
    """Splits text into chunks based on paragraphs (double newlines)."""
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]

def chunk_text(text: str, strategy: str) -> List[str]:
    """Routes text to the appropriate chunking strategy."""
    logger.info(f"Applying chunking strategy: {strategy}")
    
    if strategy == "fixed":
        chunks = chunk_fixed_size(text)
    elif strategy == "sentence":
        chunks = chunk_sentences(text)
    elif strategy == "paragraph":
        chunks = chunk_paragraphs(text)
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")
        
    logger.info(f"Created {len(chunks)} chunks.")
    return chunks


# ==============================================================================
# Embedding Generation
# ==============================================================================

def generate_embeddings(chunks: List[str]) -> List[List[float]]:
    """Generates vector embeddings for a list of text chunks using Gemini."""
    logger.info(f"Generating embeddings for {len(chunks)} chunks using {EMBEDDING_MODEL}...")
    embeddings = []
    
    # Process in batches or one by one. Google's API can handle multiple, 
    # but we'll do it iteratively for simplicity and better error tracking per chunk.
    try:
        for i, chunk in enumerate(chunks):
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=chunk
            )
            embeddings.append(response.embeddings[0].values)
            
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(chunks)} embeddings...")
                
        logger.info("Successfully generated all embeddings.")
        return embeddings
        
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise


# ==============================================================================
# Database Operations
# ==============================================================================

def setup_database(conn: pg_conn) -> None:
    """Ensures the pgvector extension and necessary table exist."""
    try:
        with conn.cursor() as cur:
            logger.info("Setting up database schema...")
            # Ensure pgvector extension is enabled
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # The embedding dimension depends on the model. gemini-embedding-001 is 768.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    chunk_text TEXT NOT NULL,
                    strategy_split VARCHAR(50) NOT NULL,
                    embedding VECTOR(768),
                    at_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to setup database: {e}")
        raise

def save_to_database(
    conn: pg_conn, 
    filename: str, 
    chunks: List[str], 
    embeddings: List[List[float]], 
    strategy: str
) -> None:
    """Saves the text chunks and their embeddings to the PostgreSQL database."""
    logger.info(f"Saving {len(chunks)} records to database...")
    
    if len(chunks) != len(embeddings):
        raise ValueError("Mismatch between number of chunks and embeddings")
        
    try:
        # Register the vector type with psycopg2 for this connection
        register_vector(conn)
        
        with conn.cursor() as cur:
            for chunk, emb in zip(chunks, embeddings):
                cur.execute(
                    """
                    INSERT INTO document_chunks 
                    (filename, chunk_text, strategy_split, embedding) 
                    VALUES (%s, %s, %s, %s)
                    """,
                    (filename, chunk, strategy, emb)
                )
        conn.commit()
        logger.info("Successfully saved all records to database.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save records to database: {e}")
        raise


# ==============================================================================
# Main Orchestrator
# ==============================================================================

def process_document(file_path: str, strategy: str) -> None:
    """Orchestrates the entire ingestion and vectorization pipeline."""
    if not GEMINI_API_KEY or not POSTGRES_URL:
        logger.error("Missing required environment variables. Aborting.")
        return

    logger.info("=== Starting Document Ingestion Pipeline ===")
    filename = Path(file_path).name
    
    # 1. Extract Text
    text = extract_text(file_path)
    if not text:
        logger.warning(f"No text extracted from {file_path}. Aborting.")
        return

    # 2. Chunk Text
    chunks = chunk_text(text, strategy)
    if not chunks:
        logger.warning("No chunks created. Aborting.")
        return

    # 3. Generate Embeddings
    embeddings = generate_embeddings(chunks)

    # 4. Save to Database
    logger.info(f"Connecting to database at {POSTGRES_URL.split('@')[-1]}...") # Don't log credentials
    conn = None
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        setup_database(conn)
        save_to_database(conn, filename, chunks, embeddings, strategy)
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")
            
    logger.info("=== Pipeline Execution Complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest a PDF or DOCX file, chunk the text, generate embeddings via Gemini, and store in PostgreSQL."
    )
    parser.add_argument(
        "file_path", 
        type=str, 
        help="Path to the PDF or DOCX file to process"
    )
    parser.add_argument(
        "--strategy", 
        type=str, 
        choices=["fixed", "sentence", "paragraph"], 
        default="paragraph",
        help="The chunking strategy to apply (default: paragraph)"
    )

    args = parser.parse_args()
    process_document(args.file_path, args.strategy)
