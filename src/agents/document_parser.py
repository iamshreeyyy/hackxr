"""
Document Parser Agent
Intelligently extracts content while preserving document structure
"""

import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
from abc import ABC, abstractmethod

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class DocumentParser(ABC):
    """Abstract base class for document parsers"""
    
    @abstractmethod
    async def parse(self, file_path: str) -> Dict[str, Any]:
        """Parse document and extract content"""
        pass

class PDFParser(DocumentParser):
    """PDF document parser"""
    
    def __init__(self):
        try:
            import PyPDF2
            import fitz  # PyMuPDF
            self.pdf_libraries_available = True
        except ImportError:
            logger.warning("PDF parsing libraries not available. Install PyPDF2 and PyMuPDF")
            self.pdf_libraries_available = False
    
    async def parse(self, file_path: str) -> Dict[str, Any]:
        """Parse PDF document"""
        if not self.pdf_libraries_available:
            return {"content": "", "metadata": {}, "pages": []}
            
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(file_path)
            content = ""
            pages = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                content += page_text + "\n"
                pages.append({
                    "page_number": page_num + 1,
                    "content": page_text,
                    "word_count": len(page_text.split())
                })
            
            doc.close()
            
            return {
                "content": content,
                "metadata": {
                    "total_pages": len(pages),
                    "file_type": "pdf",
                    "file_name": Path(file_path).name
                },
                "pages": pages
            }
            
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {str(e)}")
            return {"content": "", "metadata": {}, "pages": []}

class WordParser(DocumentParser):
    """Word document parser"""
    
    def __init__(self):
        try:
            import docx
            self.docx_available = True
        except ImportError:
            logger.warning("Word parsing library not available. Install python-docx")
            self.docx_available = False
    
    async def parse(self, file_path: str) -> Dict[str, Any]:
        """Parse Word document"""
        if not self.docx_available:
            return {"content": "", "metadata": {}, "paragraphs": []}
            
        try:
            import docx
            
            doc = docx.Document(file_path)
            content = ""
            paragraphs = []
            
            for i, para in enumerate(doc.paragraphs):
                if para.text.strip():
                    content += para.text + "\n"
                    paragraphs.append({
                        "paragraph_number": i + 1,
                        "content": para.text,
                        "style": para.style.name if para.style else "Normal"
                    })
            
            return {
                "content": content,
                "metadata": {
                    "total_paragraphs": len(paragraphs),
                    "file_type": "docx",
                    "file_name": Path(file_path).name
                },
                "paragraphs": paragraphs
            }
            
        except Exception as e:
            logger.error(f"Error parsing Word document {file_path}: {str(e)}")
            return {"content": "", "metadata": {}, "paragraphs": []}

class TextParser(DocumentParser):
    """Plain text parser"""
    
    async def parse(self, file_path: str) -> Dict[str, Any]:
        """Parse text document"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            lines = content.split('\n')
            return {
                "content": content,
                "metadata": {
                    "total_lines": len(lines),
                    "file_type": "txt",
                    "file_name": Path(file_path).name
                },
                "lines": [{"line_number": i+1, "content": line} for i, line in enumerate(lines)]
            }
            
        except Exception as e:
            logger.error(f"Error parsing text file {file_path}: {str(e)}")
            return {"content": "", "metadata": {}, "lines": []}

class DocumentParserAgent:
    """
    Document Parser Agent
    Intelligently extracts content while preserving document structure
    """
    
    def __init__(self):
        self.parsers = {
            '.pdf': PDFParser(),
            '.docx': WordParser(),
            '.doc': WordParser(),
            '.txt': TextParser(),
        }
        logger.info("Document Parser Agent initialized")
    
    async def parse_document(self, file_path: str) -> Dict[str, Any]:
        """
        Parse document based on file extension
        
        Args:
            file_path: Path to the document
            
        Returns:
            Parsed document data
        """
        try:
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension not in self.parsers:
                logger.warning(f"Unsupported file type: {file_extension}")
                return {
                    "content": "",
                    "metadata": {"error": f"Unsupported file type: {file_extension}"},
                    "success": False
                }
            
            parser = self.parsers[file_extension]
            result = await parser.parse(file_path)
            result["success"] = True
            
            logger.info(f"Successfully parsed {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error in document parsing: {str(e)}")
            return {
                "content": "",
                "metadata": {"error": str(e)},
                "success": False
            }
    
    async def extract_structure(self, parsed_document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structural elements from parsed document
        
        Args:
            parsed_document: Parsed document data
            
        Returns:
            Document structure information
        """
        try:
            content = parsed_document.get("content", "")
            
            # Simple structure extraction - can be enhanced with more sophisticated NLP
            structure = {
                "headings": self._extract_headings(content),
                "sections": self._extract_sections(content),
                "lists": self._extract_lists(content),
                "tables": self._extract_tables(content)
            }
            
            return structure
            
        except Exception as e:
            logger.error(f"Error extracting structure: {str(e)}")
            return {}
    
    def _extract_headings(self, content: str) -> List[Dict[str, Any]]:
        """Extract potential headings from content"""
        headings = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line and (line.isupper() or line.endswith(':') or len(line.split()) < 10):
                headings.append({
                    "line_number": i + 1,
                    "text": line,
                    "level": self._determine_heading_level(line)
                })
        
        return headings
    
    def _determine_heading_level(self, text: str) -> int:
        """Determine heading level based on text characteristics"""
        if text.isupper():
            return 1
        elif text.endswith(':'):
            return 2
        else:
            return 3
    
    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """Extract sections from content"""
        # Simple section detection based on common patterns
        sections = []
        lines = content.split('\n')
        current_section = ""
        section_start = 0
        
        for i, line in enumerate(lines):
            if line.strip() and (line.isupper() or line.endswith(':')):
                if current_section:
                    sections.append({
                        "start_line": section_start,
                        "end_line": i,
                        "title": lines[section_start].strip(),
                        "content": current_section
                    })
                current_section = ""
                section_start = i
            else:
                current_section += line + "\n"
        
        if current_section:
            sections.append({
                "start_line": section_start,
                "end_line": len(lines),
                "title": lines[section_start].strip() if section_start < len(lines) else "",
                "content": current_section
            })
        
        return sections
    
    def _extract_lists(self, content: str) -> List[Dict[str, Any]]:
        """Extract lists from content"""
        lists = []
        lines = content.split('\n')
        current_list = []
        list_start = -1
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line and (line.startswith('•') or line.startswith('-') or 
                        line.startswith('*') or line[0:2].isdigit()):
                if list_start == -1:
                    list_start = i
                current_list.append(line)
            else:
                if current_list:
                    lists.append({
                        "start_line": list_start + 1,
                        "end_line": i,
                        "items": current_list,
                        "type": "bullet" if current_list[0].startswith(('•', '-', '*')) else "numbered"
                    })
                current_list = []
                list_start = -1
        
        if current_list:
            lists.append({
                "start_line": list_start + 1,
                "end_line": len(lines),
                "items": current_list,
                "type": "bullet" if current_list[0].startswith(('•', '-', '*')) else "numbered"
            })
        
        return lists
    
    def _extract_tables(self, content: str) -> List[Dict[str, Any]]:
        """Extract potential tables from content"""
        # Simple table detection - can be enhanced
        tables = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if '|' in line and line.count('|') >= 2:
                # Potential table row
                cells = [cell.strip() for cell in line.split('|')]
                tables.append({
                    "line_number": i + 1,
                    "cells": cells,
                    "column_count": len(cells)
                })
        
        return tables
