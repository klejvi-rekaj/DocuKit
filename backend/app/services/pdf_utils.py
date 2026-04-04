import io
import logging
import pdfplumber
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts text and page metadata from a PDF provided as bytes.
    Returns a dictionary containing:
        - 'pages': int (total pages)
        - 'content': List[Dict] with 'page_number' and 'text'.
        - 'text_summary': str (first few characters for summary)
    """
    content = []
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                # Normalize text and strip excess whitespace
                clean_text = " ".join(text.split()) if text else ""
                content.append({
                    "page_number": i + 1,
                    "text": clean_text
                })
                
            # Create a short summary from the first valid page
            text_summary = ""
            for p in content:
                if p["text"]:
                    text_summary = p["text"][:200] + "..."
                    break
                    
        return {
            "status": "success",
            "pages": total_pages,
            "content": content,
            "text_summary": text_summary,
            "error": None
        }
    except Exception as e:
        logger.error(f"Error extracting PDF: {e}")
        return {
            "status": "error",
            "pages": 0,
            "content": [],
            "text_summary": "",
            "error": str(e)
        }

def fast_extract_metadata(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extremely fast metadata extraction without full text parsing."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
            # Only extract first page for summary
            first_page_text = ""
            if total_pages > 0:
                first_page_text = pdf.pages[0].extract_text()
                first_page_text = " ".join(first_page_text.split()) if first_page_text else ""
            
            return {
                "pages": total_pages,
                "text_summary": first_page_text[:200] + "..." if first_page_text else "New PDF Upload"
            }
    except Exception as e:
        logger.error(f"Fast extraction failed: {e}")
        return {"pages": 0, "text_summary": "Processing..."}
