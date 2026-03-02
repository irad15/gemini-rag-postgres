# Part Two - Writing a Python Module

Develop a Python module that implements a document vector creation process, consisting of a single Python script:

## `index_documents.py`
* **Input:** A PDF or .DOCX file (must be able to accept both).
* **Extraction:** Extract clean text from the file.
* **Chunking:** Split the text into segments (Chunks) using one of three strategies:
  1. Fixed-size with overlap
  2. Sentence-based splitting
  3. Paragraph-based splitting
* **Embedding:** Generate an Embedding for each chunk using the Google Gemini API.
* **Storage:** Save the chunks along with their vectors in a PostgreSQL database.

## PostgreSQL Database Structure
Ensure the database includes the following columns:
* `id`: Unique identifier
* `chunk_text`: The chunk text
* `embedding`: The embedding vector
* `filename`: The original file name
* `strategy_split`: The chosen splitting strategy
* `at_created`: Date added (optional)

## Security Requirements
* Do not save API keys or connection details in the code.
* Use a `.env` file with the appropriate variables (`GEMINI_API_KEY`, `POSTGRES_URL`).

## Submission Requirements
* A GitHub link to the script.
* A `README.md` file with clear explanations regarding installation, execution, and usage examples.
* Clean, documented, and modular code.