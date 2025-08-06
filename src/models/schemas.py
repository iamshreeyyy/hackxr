"""
Pydantic models for request/response schemas
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class QueryRequest(BaseModel):
    """Request schema for query processing"""
    query: str = Field(..., description="Natural language query to process")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the query")

class SourceClause(BaseModel):
    """Schema for source clause information"""
    document_name: str = Field(..., description="Name of the source document")
    clause_id: str = Field(..., description="Unique identifier for the clause")
    clause_text: str = Field(..., description="Full text of the relevant clause")
    relevance_score: float = Field(..., description="Relevance score for this clause")
    page_number: Optional[int] = Field(None, description="Page number in source document")

class QueryResponse(BaseModel):
    """Response schema for query processing"""
    query: str = Field(..., description="Original query")
    decision: str = Field(..., description="Decision result (approved/rejected/pending)")
    amount: Optional[float] = Field(None, description="Amount if applicable")
    justification: str = Field(..., description="Detailed justification for the decision")
    confidence_score: float = Field(..., description="Confidence score (0-1)")
    source_clauses: List[SourceClause] = Field(..., description="Source clauses used for decision")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now)

class DocumentUploadResponse(BaseModel):
    """Response schema for document upload"""
    message: str = Field(..., description="Upload status message")
    files_processed: List[Dict[str, Any]] = Field(..., description="Details of processed files")
    total_documents: int = Field(..., description="Total number of documents processed")
    timestamp: datetime = Field(default_factory=datetime.now)

class ParsedEntity(BaseModel):
    """Schema for parsed entities from query"""
    entity_type: str = Field(..., description="Type of entity (age, procedure, location, etc.)")
    value: str = Field(..., description="Extracted value")
    confidence: float = Field(..., description="Confidence in extraction")

class DocumentChunk(BaseModel):
    """Schema for document chunks"""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk content")
    document_source: str = Field(..., description="Source document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    dense_embedding: Optional[List[float]] = Field(None, description="Dense vector embedding")
    sparse_embedding: Optional[Dict[str, float]] = Field(None, description="Sparse vector embedding")

class ValidationRule(BaseModel):
    """Schema for validation rules"""
    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    condition: str = Field(..., description="Rule condition")
    action: str = Field(..., description="Action to take if condition is met")
    priority: int = Field(default=1, description="Rule priority")

class AgentStatus(BaseModel):
    """Schema for agent status"""
    agent_name: str = Field(..., description="Name of the agent")
    status: str = Field(..., description="Current status")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    processed_items: int = Field(default=0, description="Number of items processed")
