import os
import sys
import glob

# Add the parent directory /backend to python path so 'app' module imports work properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import settings
from app.services.pdf_utils import extract_text_from_pdf_bytes
from app.services.rag_utils import process_and_index_document, vector_store

def rebuild_index():
    print("Rebuilding FAISS index from stored PDFs...")
    uploads_dir = settings.pdf_upload_dir
    
    if not os.path.exists(uploads_dir):
        print(f"Directory {uploads_dir} not found. Nothing to rebuild.")
        return

    pdf_files = glob.glob(os.path.join(uploads_dir, "*.pdf"))
    if not pdf_files:
        print("No PDF files found to index.")
        return
        
    # Reset existing FAISS index
    print("Clearing existing index...")
    # By recreating the file with an empty dictionary and re-initializing the store, we start fresh.
    metadata_path = settings.faiss_index_path.replace('.bin', '_meta.json')
    if os.path.exists(settings.faiss_index_path):
        os.remove(settings.faiss_index_path)
    if os.path.exists(metadata_path):
        os.remove(metadata_path)
        
    # Re-initialize the global store from scratch
    vector_store._load_index()

    total_chunks = 0
    for file_path in pdf_files:
        file_name = os.path.basename(file_path)
        file_id = os.path.splitext(file_name)[0]
        
        print(f"Processing {file_id}...")
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
                
            extraction = extract_text_from_pdf_bytes(file_bytes)
            if extraction["status"] == "success":
                chunks = process_and_index_document(file_id, extraction["content"])
                print(f"  -> Added {chunks} chunks.")
                total_chunks += chunks
            else:
                print(f"  -> Extraction failed: {extraction.get('error')}")
                
        except Exception as e:
            print(f"  -> Error reading file {file_path}: {e}")
            
    print(f"Rebuild completed successfully. {len(pdf_files)} files processed. {total_chunks} total chunks indexed.")

if __name__ == "__main__":
    rebuild_index()
