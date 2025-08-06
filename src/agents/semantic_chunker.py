"""
Semantic Chunker Agent
Creates contextually-aware text segments, not arbitrary size-based chunks
"""

import asyncio
import re
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass

from src.utils.logger import setup_logger
from src.models.schemas import DocumentChunk

logger = setup_logger(__name__)

@dataclass
class ChunkingConfig:
    """Configuration for semantic chunking"""
    max_chunk_size: int = 512
    min_chunk_size: int = 50
    overlap_size: int = 50
    semantic_threshold: float = 0.7
    preserve_sentences: bool = True
    preserve_paragraphs: bool = True

class SemanticChunkerAgent:
    """
    Semantic Chunker Agent
    Creates contextually-aware text segments that keep related ideas together
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
        self.sentence_endings = re.compile(r'[.!?]+')
        self.paragraph_breaks = re.compile(r'\n\s*\n')
        logger.info("Semantic Chunker Agent initialized")
    
    async def create_chunks(self, document_content: str, document_source: str) -> List[DocumentChunk]:
        """
        Create semantic chunks from document content
        
        Args:
            document_content: Raw document text
            document_source: Source document identifier
            
        Returns:
            List of semantic chunks
        """
        try:
            # Pre-process the content
            cleaned_content = self._preprocess_content(document_content)
            
            # Extract structural elements
            paragraphs = self._extract_paragraphs(cleaned_content)
            
            # Create semantic chunks
            chunks = []
            for i, paragraph in enumerate(paragraphs):
                paragraph_chunks = await self._chunk_paragraph(
                    paragraph, document_source, i
                )
                chunks.extend(paragraph_chunks)
            
            # Post-process chunks for optimal size and overlap
            optimized_chunks = self._optimize_chunks(chunks)
            
            logger.info(f"Created {len(optimized_chunks)} semantic chunks for {document_source}")
            return optimized_chunks
            
        except Exception as e:
            logger.error(f"Error creating chunks: {str(e)}")
            return []
    
    def _preprocess_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Normalize line breaks
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Remove special characters that might interfere
        content = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)\[\]\n]', '', content)
        
        return content.strip()
    
    def _extract_paragraphs(self, content: str) -> List[str]:
        """Extract paragraphs from content"""
        if self.config.preserve_paragraphs:
            paragraphs = self.paragraph_breaks.split(content)
            return [p.strip() for p in paragraphs if p.strip()]
        else:
            return [content]  # Treat entire content as one paragraph
    
    async def _chunk_paragraph(self, paragraph: str, source: str, paragraph_index: int) -> List[DocumentChunk]:
        """Create chunks from a single paragraph"""
        if len(paragraph) <= self.config.max_chunk_size:
            # Paragraph is small enough to be a single chunk
            return [self._create_chunk(paragraph, source, paragraph_index, 0)]
        
        # Split paragraph into sentences
        sentences = self._extract_sentences(paragraph)
        
        # Group sentences into chunks
        chunks = []
        current_chunk = ""
        sentence_indices = []
        
        for i, sentence in enumerate(sentences):
            # Check if adding this sentence would exceed max size
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) > self.config.max_chunk_size and current_chunk:
                # Create chunk from current content
                if len(current_chunk) >= self.config.min_chunk_size:
                    chunk = self._create_chunk(
                        current_chunk.strip(), 
                        source, 
                        paragraph_index, 
                        len(chunks)
                    )
                    chunks.append(chunk)
                
                # Start new chunk with overlap
                current_chunk = self._add_overlap(chunks, sentence)
                sentence_indices = [i]
            else:
                current_chunk = potential_chunk
                sentence_indices.append(i)
        
        # Add final chunk
        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunk = self._create_chunk(
                current_chunk.strip(), 
                source, 
                paragraph_index, 
                len(chunks)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _extract_sentences(self, text: str) -> List[str]:
        """Extract sentences from text"""
        if not self.config.preserve_sentences:
            # Simple word-based splitting
            words = text.split()
            sentences = []
            for i in range(0, len(words), 20):  # Arbitrary sentence length
                sentences.append(" ".join(words[i:i+20]))
            return sentences
        
        # Split by sentence endings
        sentences = self.sentence_endings.split(text)
        
        # Clean and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Filter very short fragments
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _create_chunk(self, content: str, source: str, paragraph_index: int, chunk_index: int) -> DocumentChunk:
        """Create a DocumentChunk object"""
        chunk_id = f"{source}_p{paragraph_index}_c{chunk_index}"
        
        # Extract key phrases for metadata
        key_phrases = self._extract_key_phrases(content)
        
        metadata = {
            "paragraph_index": paragraph_index,
            "chunk_index": chunk_index,
            "word_count": len(content.split()),
            "character_count": len(content),
            "key_phrases": key_phrases,
            "chunk_type": self._determine_chunk_type(content)
        }
        
        return DocumentChunk(
            chunk_id=chunk_id,
            content=content,
            document_source=source,
            metadata=metadata
        )
    
    def _add_overlap(self, existing_chunks: List[DocumentChunk], new_sentence: str) -> str:
        """Add overlap from previous chunk to new chunk"""
        if not existing_chunks or self.config.overlap_size == 0:
            return new_sentence
        
        previous_content = existing_chunks[-1].content
        words = previous_content.split()
        
        if len(words) > self.config.overlap_size:
            overlap_words = words[-self.config.overlap_size:]
            overlap_text = " ".join(overlap_words)
            return overlap_text + " " + new_sentence
        
        return previous_content + " " + new_sentence
    
    def _extract_key_phrases(self, content: str) -> List[str]:
        """Extract key phrases from content for metadata"""
        # Simple key phrase extraction - can be enhanced with NLP libraries
        words = content.lower().split()
        
        # Filter common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
        
        key_words = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Find phrases (simple bigrams and trigrams)
        phrases = []
        for i in range(len(key_words) - 1):
            bigram = " ".join(key_words[i:i+2])
            if len(bigram) > 6:
                phrases.append(bigram)
        
        for i in range(len(key_words) - 2):
            trigram = " ".join(key_words[i:i+3])
            if len(trigram) > 10:
                phrases.append(trigram)
        
        # Return most frequent phrases
        phrase_freq = {}
        for phrase in phrases:
            phrase_freq[phrase] = phrase_freq.get(phrase, 0) + 1
        
        sorted_phrases = sorted(phrase_freq.items(), key=lambda x: x[1], reverse=True)
        return [phrase for phrase, freq in sorted_phrases[:5]]
    
    def _determine_chunk_type(self, content: str) -> str:
        """Determine the type of chunk based on content characteristics"""
        content_lower = content.lower()
        
        # Policy-specific patterns
        if any(word in content_lower for word in ['policy', 'coverage', 'premium', 'deductible']):
            return 'policy_clause'
        elif any(word in content_lower for word in ['waiting', 'period', 'eligible', 'claim']):
            return 'eligibility_rule'
        elif any(word in content_lower for word in ['amount', 'payment', 'reimbursement', '$']):
            return 'financial_clause'
        elif any(word in content_lower for word in ['exclusion', 'not covered', 'limitation']):
            return 'exclusion_clause'
        elif content.count(':') > 2 or content.count('|') > 2:
            return 'structured_data'
        else:
            return 'general_content'
    
    def _optimize_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Optimize chunks for better retrieval performance"""
        optimized = []
        
        for chunk in chunks:
            # Ensure minimum size
            if len(chunk.content) < self.config.min_chunk_size:
                # Try to merge with previous chunk if possible
                if optimized and len(optimized[-1].content) + len(chunk.content) < self.config.max_chunk_size:
                    merged_content = optimized[-1].content + " " + chunk.content
                    optimized[-1].content = merged_content
                    optimized[-1].metadata['word_count'] = len(merged_content.split())
                    optimized[-1].metadata['character_count'] = len(merged_content)
                    continue
            
            optimized.append(chunk)
        
        return optimized
    
    async def create_contextual_chunks(self, content: str, source: str, context_window: int = 3) -> List[DocumentChunk]:
        """
        Create chunks with enhanced context awareness
        
        Args:
            content: Document content
            source: Source identifier
            context_window: Number of surrounding chunks to consider for context
            
        Returns:
            List of contextually-aware chunks
        """
        # Create initial chunks
        base_chunks = await self.create_chunks(content, source)
        
        # Enhance with contextual information
        for i, chunk in enumerate(base_chunks):
            context_before = []
            context_after = []
            
            # Collect context from surrounding chunks
            for j in range(max(0, i - context_window), min(len(base_chunks), i + context_window + 1)):
                if j < i:
                    context_before.append(base_chunks[j].content[:100])  # First 100 chars
                elif j > i:
                    context_after.append(base_chunks[j].content[:100])   # First 100 chars
            
            # Add context to metadata
            chunk.metadata['context_before'] = context_before
            chunk.metadata['context_after'] = context_after
            chunk.metadata['chunk_position'] = i
            chunk.metadata['total_chunks'] = len(base_chunks)
        
        return base_chunks
