"""
LLM-Powered Intelligent Query-Retrieval System
Main FastAPI application entry point
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn
import logging
from pathlib import Path

from src.models.schemas import QueryRequest, QueryResponse, DocumentUploadResponse
from src.agents.orchestrator import AgentOrchestrator
from src.utils.logger import setup_logger
from src.config import get_settings, validate_configuration, print_configuration

# Setup logging
logger = setup_logger(__name__)

# Get settings
settings = get_settings()

# Validate configuration
config_issues = validate_configuration()
if config_issues:
    logger.error("Configuration issues found:")
    for issue in config_issues:
        logger.error(f"  - {issue}")
    exit(1)

# Print configuration
print_configuration()

# Create FastAPI app
app = FastAPI(
    title="LLM Document Processing System",
    description="Multi-agent RAG system for intelligent document processing and query retrieval",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = AgentOrchestrator()

@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup"""
    logger.info("Starting LLM Document Processing System...")
    await orchestrator.initialize()
    logger.info("System initialization complete")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "LLM Document Processing System",
        "status": "active",
        "version": "1.0.0"
    }

@app.post("/upload-documents", response_model=DocumentUploadResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Upload and process documents for the knowledge base
    """
    try:
        logger.info(f"Uploading {len(files)} documents")
        
        # Process uploaded files
        processed_files = []
        for file in files:
            if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]:
                logger.warning(f"Unsupported file type: {file.content_type}")
                continue
                
            # Save file temporarily
            file_path = f"/tmp/{file.filename}"
            content = await file.read()
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Process document through orchestrator
            result = await orchestrator.process_document(file_path)
            processed_files.append({
                "filename": file.filename,
                "status": "processed" if result else "failed",
                "chunks_created": result.get("chunks", 0) if result else 0
            })
            
        return DocumentUploadResponse(
            message=f"Processed {len(processed_files)} documents",
            files_processed=processed_files,
            total_documents=len(processed_files)
        )
        
    except Exception as e:
        logger.error(f"Error uploading documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a natural language query and return structured response
    """
    try:
        logger.info(f"Processing query: {request.query}")
        
        # Process query through the multi-agent system
        result = await orchestrator.process_query(request.query)
        
        return QueryResponse(
            query=request.query,
            decision=result["decision"],
            amount=result.get("amount"),
            justification=result["justification"],
            confidence_score=result["confidence_score"],
            source_clauses=result["source_clauses"],
            processing_time=result["processing_time"]
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "agents_status": await orchestrator.get_system_status(),
        "vector_db_status": "connected"
    }

@app.get("/system-info")
async def get_system_info():
    """Get system information and statistics"""
    return await orchestrator.get_system_info()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
