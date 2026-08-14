import os
from typing import Dict, Any

from brain.schemas import AttachmentMetadata
from brain.parsers import (
    get_file_size_and_checksum,
    format_size,
    parse_pdf,
    parse_docx,
    parse_image,
    parse_zip,
    parse_csv,
    parse_txt
)

SUPPORTED_EXTENSIONS = {
    # PDF
    ".pdf": "pdf",
    # DOCX
    ".docx": "docx",
    # TXT
    ".txt": "txt",
    # CSV
    ".csv": "csv",
    # Images
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".bmp": "image",
    ".tiff": "image",
    # ZIP
    ".zip": "zip"
}

def analyze_attachment(attachment: Dict[str, Any]) -> AttachmentMetadata:
    """
    Analyzes a file attachment.
    Expects attachment dict to have 'path' (absolute path to file) and optionally 'name'.
    If file format is unsupported, raises ValueError.
    """
    file_path = attachment.get("path")
    if not file_path:
        raise ValueError("Attachment missing 'path'")
        
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Attachment file not found at: {file_path}")
        
    file_name = attachment.get("name") or os.path.basename(file_path)
    _, ext = os.path.splitext(file_name.lower())
    
    # 1. Reject unsupported files
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {ext or 'no extension'}")
        
    file_type = SUPPORTED_EXTENSIONS[ext]
    
    # 2. Get file size and checksum
    size_bytes, checksum = get_file_size_and_checksum(file_path)
    formatted_size = format_size(size_bytes)
    
    # 3. Call parser based on file type
    pages = 1
    metadata = {}
    
    if file_type == "pdf":
        res = parse_pdf(file_path)
        pages, metadata = res["pages"], res["metadata"]
    elif file_type == "docx":
        res = parse_docx(file_path)
        pages, metadata = res["pages"], res["metadata"]
    elif file_type == "image":
        res = parse_image(file_path)
        pages, metadata = res["pages"], res["metadata"]
    elif file_type == "zip":
        res = parse_zip(file_path)
        pages, metadata = res["pages"], res["metadata"]
    elif file_type == "csv":
        res = parse_csv(file_path)
        pages, metadata = res["pages"], res["metadata"]
    elif file_type == "txt":
        res = parse_txt(file_path)
        pages, metadata = res["pages"], res["metadata"]
        
    return AttachmentMetadata(
        name=file_name,
        type=file_type,
        pages=pages,
        size=formatted_size,
        checksum=checksum,
        metadata=metadata
    )
