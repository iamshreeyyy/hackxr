<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Copilot Instructions for LLM-Powered Query-Retrieval System

This is a sophisticated multi-agent RAG system with hybrid vector architecture. When working on this project:

## Core Architecture Principles
- Follow the 6-agent specialization pattern: Document Parser, Semantic Chunker, Retrieval, Validation, Decision, and Mapping agents
- Implement hybrid dense-sparse vector search for optimal precision and recall
- Maintain bidirectional traceability between decisions and source documents
- Generate explainable decisions with clause-level justification

## Code Style Guidelines
- Use type hints throughout the codebase
- Follow async/await patterns for I/O operations
- Implement proper error handling and logging
- Use Pydantic models for data validation
- Follow the agent-based architecture pattern

## Key Technologies
- FastAPI for API endpoints
- LangChain for LLM operations
- ChromaDB/FAISS for vector storage
- Sentence Transformers for embeddings
- SpaCy for NLP processing

## Testing Considerations
- Test each agent independently
- Validate vector search performance
- Test policy validation rules
- Ensure traceability features work correctly
