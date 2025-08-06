"""
Retrieval Agent
Combines dense and sparse vector search for optimal recall and precision
"""

import asyncio
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass

from src.utils.logger import setup_logger
from src.models.schemas import DocumentChunk, SourceClause

logger = setup_logger(__name__)

@dataclass
class RetrievalConfig:
    """Configuration for retrieval operations"""
    dense_weight: float = 0.7
    sparse_weight: float = 0.3
    max_results: int = 10
    similarity_threshold: float = 0.6
    rerank_results: bool = True

class VectorStore:
    """Simple in-memory vector store implementation"""
    
    def __init__(self):
        self.dense_vectors: Dict[str, np.ndarray] = {}
        self.sparse_vectors: Dict[str, Dict[str, float]] = {}
        self.documents: Dict[str, DocumentChunk] = {}
        self.embeddings_model = None
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize sentence transformer model for embeddings"""
        try:
            from sentence_transformers import SentenceTransformer
            self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence transformer model loaded successfully")
        except ImportError:
            logger.warning("sentence-transformers not available. Using mock embeddings.")
            self.embeddings_model = None
    
    async def add_document(self, chunk: DocumentChunk) -> bool:
        """Add document chunk to vector store"""
        try:
            # Generate dense embedding
            dense_embedding = await self._generate_dense_embedding(chunk.content)
            
            # Generate sparse embedding
            sparse_embedding = self._generate_sparse_embedding(chunk.content)
            
            # Store vectors and document
            self.dense_vectors[chunk.chunk_id] = dense_embedding
            self.sparse_vectors[chunk.chunk_id] = sparse_embedding
            self.documents[chunk.chunk_id] = chunk
            
            # Update chunk with embeddings
            chunk.dense_embedding = dense_embedding.tolist()
            chunk.sparse_embedding = sparse_embedding
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding document to vector store: {str(e)}")
            return False
    
    async def _generate_dense_embedding(self, text: str) -> np.ndarray:
        """Generate dense vector embedding"""
        if self.embeddings_model:
            try:
                embedding = self.embeddings_model.encode(text)
                return np.array(embedding)
            except Exception as e:
                logger.error(f"Error generating dense embedding: {str(e)}")
        
        # Fallback: simple word-based embedding
        words = text.lower().split()
        vocab_size = 1000  # Simple vocabulary size
        embedding = np.zeros(384)  # Match sentence transformer dimension
        
        for i, word in enumerate(words[:50]):  # Use first 50 words
            word_hash = hash(word) % vocab_size
            embedding[word_hash % 384] += 1.0
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding
    
    def _generate_sparse_embedding(self, text: str) -> Dict[str, float]:
        """Generate sparse vector embedding (TF-IDF like)"""
        words = text.lower().split()
        word_freq = {}
        
        # Count word frequencies
        for word in words:
            if len(word) > 2:  # Filter very short words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Simple TF normalization
        total_words = len(words)
        sparse_vector = {}
        
        for word, freq in word_freq.items():
            tf = freq / total_words
            sparse_vector[word] = tf
        
        return sparse_vector
    
    async def similarity_search(self, query: str, config: RetrievalConfig) -> List[Tuple[str, float]]:
        """Perform similarity search using hybrid approach"""
        try:
            # Generate query embeddings
            query_dense = await self._generate_dense_embedding(query)
            query_sparse = self._generate_sparse_embedding(query)
            
            # Calculate similarities
            similarities = []
            
            for doc_id in self.documents:
                dense_sim = self._cosine_similarity(query_dense, self.dense_vectors[doc_id])
                sparse_sim = self._sparse_similarity(query_sparse, self.sparse_vectors[doc_id])
                
                # Combine similarities
                hybrid_score = (config.dense_weight * dense_sim + 
                              config.sparse_weight * sparse_sim)
                
                if hybrid_score >= config.similarity_threshold:
                    similarities.append((doc_id, hybrid_score))
            
            # Sort by similarity score
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities[:config.max_results]
            
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            return []
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between dense vectors"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return dot_product / (norm1 * norm2)
        except:
            return 0.0
    
    def _sparse_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Calculate similarity between sparse vectors"""
        if not vec1 or not vec2:
            return 0.0
        
        # Calculate dot product
        dot_product = 0.0
        for word in vec1:
            if word in vec2:
                dot_product += vec1[word] * vec2[word]
        
        # Calculate norms
        norm1 = sum(val ** 2 for val in vec1.values()) ** 0.5
        norm2 = sum(val ** 2 for val in vec2.values()) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)

class QueryParser:
    """Parse and structure queries to extract entities"""
    
    def __init__(self):
        self.entity_patterns = {
            'age': r'\b(\d+)[-\s]?(?:year|yr|y)[-\s]?old|\b(\d+)[yY]\b|\b(\d+)\s*male|\b(\d+)\s*female',
            'gender': r'\b(male|female|man|woman|M|F)\b',
            'procedure': r'\b(surgery|operation|treatment|procedure|knee|hip|heart|brain|cancer|diabetes)\b',
            'location': r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b(?=\s*(?:city|state|hospital|clinic)|\s*,)',
            'policy_duration': r'\b(\d+)[-\s]?(?:month|yr|year)[-\s]?old\s+(?:policy|insurance)',
            'amount': r'\$?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:dollars?|USD|\$)?'
        }
        logger.info("Query Parser initialized")
    
    async def parse_query(self, query: str) -> Dict[str, Any]:
        """Parse query and extract structured entities"""
        import re
        
        entities = {}
        query_lower = query.lower()
        
        # Extract entities using regex patterns
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.finditer(pattern, query, re.IGNORECASE)
            values = []
            
            for match in matches:
                # Get the first non-None group
                value = next((group for group in match.groups() if group), None)
                if value:
                    values.append(value.strip())
            
            if values:
                entities[entity_type] = values[0] if len(values) == 1 else values
        
        # Extract additional context
        context = {
            'query_length': len(query.split()),
            'contains_urgency': any(word in query_lower for word in ['urgent', 'emergency', 'asap', 'immediate']),
            'contains_negation': any(word in query_lower for word in ['not', 'no', 'never', 'without']),
            'question_type': self._determine_question_type(query_lower)
        }
        
        return {
            'original_query': query,
            'entities': entities,
            'context': context,
            'structured_query': self._build_structured_query(entities)
        }
    
    def _determine_question_type(self, query: str) -> str:
        """Determine the type of question being asked"""
        if any(word in query for word in ['eligible', 'qualify', 'covered', 'allowed']):
            return 'eligibility'
        elif any(word in query for word in ['amount', 'cost', 'price', 'pay', '$']):
            return 'financial'
        elif any(word in query for word in ['when', 'how long', 'waiting', 'period']):
            return 'timing'
        elif any(word in query for word in ['where', 'location', 'hospital', 'clinic']):
            return 'location'
        else:
            return 'general'
    
    def _build_structured_query(self, entities: Dict[str, Any]) -> str:
        """Build a structured query from extracted entities"""
        parts = []
        
        if 'age' in entities:
            parts.append(f"Age: {entities['age']}")
        if 'gender' in entities:
            parts.append(f"Gender: {entities['gender']}")
        if 'procedure' in entities:
            parts.append(f"Procedure: {entities['procedure']}")
        if 'location' in entities:
            parts.append(f"Location: {entities['location']}")
        if 'policy_duration' in entities:
            parts.append(f"Policy Duration: {entities['policy_duration']}")
        
        return " | ".join(parts) if parts else "General inquiry"

class RetrievalAgent:
    """
    Retrieval Agent
    Combines dense and sparse vector search for optimal recall and precision
    """
    
    def __init__(self, config: Optional[RetrievalConfig] = None):
        self.config = config or RetrievalConfig()
        self.vector_store = VectorStore()
        self.query_parser = QueryParser()
        logger.info("Retrieval Agent initialized")
    
    async def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """Add document chunks to the retrieval system"""
        try:
            success_count = 0
            for chunk in chunks:
                if await self.vector_store.add_document(chunk):
                    success_count += 1
            
            logger.info(f"Added {success_count}/{len(chunks)} documents to retrieval system")
            return success_count == len(chunks)
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            return False
    
    async def retrieve_relevant_documents(self, query: str) -> List[SourceClause]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: Natural language query
            
        Returns:
            List of relevant source clauses
        """
        try:
            # Parse the query
            parsed_query = await self.query_parser.parse_query(query)
            logger.info(f"Parsed query: {parsed_query['structured_query']}")
            
            # Enhance query with structured information
            enhanced_query = f"{query} {parsed_query['structured_query']}"
            
            # Perform similarity search
            similar_docs = await self.vector_store.similarity_search(enhanced_query, self.config)
            
            # Convert to SourceClause objects
            source_clauses = []
            for doc_id, similarity_score in similar_docs:
                chunk = self.vector_store.documents[doc_id]
                
                source_clause = SourceClause(
                    document_name=chunk.document_source,
                    clause_id=chunk.chunk_id,
                    clause_text=chunk.content,
                    relevance_score=similarity_score,
                    page_number=chunk.metadata.get('paragraph_index')
                )
                source_clauses.append(source_clause)
            
            # Re-rank results if enabled
            if self.config.rerank_results:
                source_clauses = await self._rerank_results(query, source_clauses, parsed_query)
            
            logger.info(f"Retrieved {len(source_clauses)} relevant documents")
            return source_clauses
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            return []
    
    async def _rerank_results(self, original_query: str, results: List[SourceClause], parsed_query: Dict[str, Any]) -> List[SourceClause]:
        """Re-rank results based on additional criteria"""
        try:
            # Simple re-ranking based on entity matching
            entity_weights = {
                'procedure': 1.5,
                'age': 1.2,
                'location': 1.3,
                'policy_duration': 1.4
            }
            
            for clause in results:
                bonus_score = 0.0
                clause_text_lower = clause.clause_text.lower()
                
                # Check for entity matches
                for entity_type, entity_value in parsed_query.get('entities', {}).items():
                    if isinstance(entity_value, str) and entity_value.lower() in clause_text_lower:
                        bonus_score += entity_weights.get(entity_type, 1.0) * 0.1
                
                # Apply bonus to relevance score
                clause.relevance_score = min(1.0, clause.relevance_score + bonus_score)
            
            # Sort by updated relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error re-ranking results: {str(e)}")
            return results
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get retrieval system statistics"""
        return {
            'total_documents': len(self.vector_store.documents),
            'vector_store_size': len(self.vector_store.dense_vectors),
            'config': {
                'dense_weight': self.config.dense_weight,
                'sparse_weight': self.config.sparse_weight,
                'max_results': self.config.max_results,
                'similarity_threshold': self.config.similarity_threshold
            }
        }
