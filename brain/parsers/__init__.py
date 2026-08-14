import os
import hashlib
import csv
import zipfile
from typing import Dict, Any, Optional

def get_file_size_and_checksum(file_path: str) -> tuple[int, str]:
    """Calculate size in bytes and SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    size = os.path.getsize(file_path)
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return size, sha256.hexdigest()

def format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable string (e.g. 8MB, 450KB)."""
    if size_bytes <= 0:
        return "0B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            # Strip trailing .0 if present
            val = f"{size_bytes:.1f}"
            if val.endswith(".0"):
                val = val[:-2]
            return f"{val}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB".replace(".0", "")

def parse_pdf(file_path: str) -> Dict[str, Any]:
    """Parse PDF document metadata and page count."""
    pages = 1
    meta = {}
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        pages = len(reader.pages)
        if reader.metadata:
            # Convert reader.metadata to a standard string dict
            meta = {str(k).replace('/', ''): str(v) for k, v in reader.metadata.items()}
    except Exception as e:
        meta["error"] = f"PDF library error or corrupt file: {str(e)}"
    
    return {
        "pages": pages,
        "metadata": meta
    }

def parse_docx(file_path: str) -> Dict[str, Any]:
    """Parse DOCX document metadata and section/page count."""
    pages = 1
    meta = {}
    try:
        from docx import Document
        doc = Document(file_path)
        
        # Word documents don't store page count directly unless compiled,
        # core_properties.pages is often 0 or None.
        props = doc.core_properties
        p_count = props.pages if props else None
        
        paragraphs = len(doc.paragraphs)
        tables = len(doc.tables)
        sections = len(doc.sections)
        
        meta = {
            "paragraphs": paragraphs,
            "tables": tables,
            "sections": sections,
            "title": props.title if props.title else "",
            "author": props.author if props.author else ""
        }
        
        if p_count and p_count > 0:
            pages = p_count
        else:
            # Estimate pages: roughly 1 page per 30 paragraphs or at least 1 section
            pages = max(1, sections, paragraphs // 30)
    except Exception as e:
        meta["error"] = f"DOCX library error or corrupt file: {str(e)}"
        
    return {
        "pages": pages,
        "metadata": meta
    }

def parse_image(file_path: str) -> Dict[str, Any]:
    """Parse Image dimensions and format details."""
    pages = 1
    meta = {}
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            meta = {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode
            }
    except Exception as e:
        meta["error"] = f"Image library error or corrupt file: {str(e)}"
        
    return {
        "pages": pages,
        "metadata": meta
    }

def parse_zip(file_path: str) -> Dict[str, Any]:
    """Parse ZIP contents listing and file count."""
    pages = 0
    meta = {}
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            file_list = z.namelist()
            pages = len(file_list)
            meta = {
                "file_count": pages,
                "files": file_list[:50]  # Limit to first 50 files for schema sanity
            }
    except Exception as e:
        meta["error"] = f"ZIP read error or corrupt file: {str(e)}"
        
    return {
        "pages": pages,
        "metadata": meta
    }

def parse_csv(file_path: str) -> Dict[str, Any]:
    """Parse CSV row and column counts."""
    pages = 1
    meta = {}
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            rows = list(reader)
            row_count = len(rows)
            col_count = len(rows[0]) if row_count > 0 else 0
            meta = {
                "rows": row_count,
                "columns": col_count
            }
    except Exception as e:
        meta["error"] = f"CSV read error: {str(e)}"
        
    return {
        "pages": pages,
        "metadata": meta
    }

def parse_txt(file_path: str) -> Dict[str, Any]:
    """Parse plain text line and character counts."""
    pages = 1
    meta = {}
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines = content.count("\n") + 1
            words = len(content.split())
            meta = {
                "lines": lines,
                "words": words,
                "characters": len(content)
            }
    except Exception as e:
        meta["error"] = f"Text read error: {str(e)}"
        
    return {
        "pages": pages,
        "metadata": meta
    }
