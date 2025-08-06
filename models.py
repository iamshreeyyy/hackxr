from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime


class DocumentMetadata(BaseModel):
    """Metadata for processed documents"""
    document_id: str
    title: Optional[str] = None
    source: Optional[str] = None
    document_type: Optional[str] = None
    upload_timestamp: datetime
    processed_timestamp: Optional[datetime] = None


class TextChunk(BaseModel):
    """Represents a semantically chunked text segment"""
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class QueryEntity(BaseModel):
    """Structured entities extracted from queries"""
    age: Optional[int] = None
    gender: Optional[str] = None
    procedure: Optional[str] = None
    location: Optional[str] = None
    policy_duration: Optional[str] = None
    additional_entities: Dict[str, Any] = {}


class QueryRequest(BaseModel):
    """Input query request"""
    query: str
    document_type: Optional[str] = None
    max_results: int = 10
    include_metadata: bool = True


class RetrievalResult(BaseModel):
    """Result from retrieval agent"""
    chunk_id: str
    document_id: str
    content: str
    relevance_score: float
    dense_score: float
    sparse_score: float
    metadata: Dict[str, Any]


class ValidationResult(BaseModel):
    """Result from validation agent"""
    is_valid: bool
    validation_rules_applied: List[str]
    violations: List[str]
    compliance_score: float


class DecisionResult(BaseModel):
    """Final decision with justification"""
    decision: str
    confidence_score: float
    justifications: List[str]
    relevant_clauses: List[str]
    supporting_documents: List[str]


class QueryResponse(BaseModel):
    """Complete query response"""
    query_id: str
    original_query: str
    extracted_entities: QueryEntity
    retrieval_results: List[RetrievalResult]
    validation_result: ValidationResult
    decision_result: DecisionResult
    processing_time_ms: int
    trace_id: str
