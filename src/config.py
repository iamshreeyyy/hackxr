"""
Configuration management for the LLM Document Processing System
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    host: str = Field(default="0.0.0.0", description="Host to bind the server")
    port: int = Field(default=8000, description="Port to bind the server")
    reload: bool = Field(default=True, description="Enable auto-reload in development")
    
    # Model Configuration (using free alternatives)
    embeddings_model: str = Field(default="all-MiniLM-L6-v2", description="Sentence transformer model")
    use_local_models: bool = Field(default=True, description="Use local models instead of API")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Document Processing Configuration
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    max_chunk_size: int = Field(default=512, description="Maximum chunk size in tokens")
    min_chunk_size: int = Field(default=50, description="Minimum chunk size in tokens")
    overlap_size: int = Field(default=50, description="Overlap size between chunks")
    
    # Vector Search Configuration
    dense_weight: float = Field(default=0.7, description="Weight for dense vector search")
    sparse_weight: float = Field(default=0.3, description="Weight for sparse vector search")
    similarity_threshold: float = Field(default=0.6, description="Minimum similarity threshold")
    max_results: int = Field(default=10, description="Maximum number of search results")
    
    # Validation Configuration
    default_age_min: int = Field(default=18, description="Default minimum age")
    default_age_max: int = Field(default=80, description="Default maximum age")
    default_waiting_period_days: int = Field(default=90, description="Default waiting period in days")
    default_max_claim_amount: float = Field(default=500000, description="Default maximum claim amount")
    
    # System Configuration
    enable_debug: bool = Field(default=False, description="Enable debug mode")
    enable_cors: bool = Field(default=True, description="Enable CORS")
    chroma_persist_directory: str = Field(default="./data/chroma", description="ChromaDB persistence directory")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings"""
    return settings

def validate_configuration():
    """Validate configuration and environment"""
    issues = []
    
    # Check required directories
    required_dirs = ["logs", "data"]
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            try:
                os.makedirs(dir_name)
            except Exception as e:
                issues.append(f"Cannot create directory {dir_name}: {str(e)}")
    
    # Validate numeric ranges
    if settings.dense_weight + settings.sparse_weight != 1.0:
        issues.append("Dense weight + Sparse weight must equal 1.0")
    
    if settings.max_chunk_size <= settings.min_chunk_size:
        issues.append("Max chunk size must be greater than min chunk size")
    
    if settings.similarity_threshold < 0 or settings.similarity_threshold > 1:
        issues.append("Similarity threshold must be between 0 and 1")
    
    # Validate age ranges
    if settings.default_age_min >= settings.default_age_max:
        issues.append("Default minimum age must be less than maximum age")
    
    return issues

def print_configuration():
    """Print current configuration (excluding secrets)"""
    print("🔧 Current Configuration:")
    print(f"   Server: {settings.host}:{settings.port}")
    print(f"   Log Level: {settings.log_level}")
    print(f"   Max File Size: {settings.max_file_size_mb}MB")
    print(f"   Chunk Size: {settings.min_chunk_size}-{settings.max_chunk_size} tokens")
    print(f"   Vector Weights: Dense={settings.dense_weight}, Sparse={settings.sparse_weight}")
    print(f"   Similarity Threshold: {settings.similarity_threshold}")
    print(f"   Age Range: {settings.default_age_min}-{settings.default_age_max} years")
    print(f"   Debug Mode: {settings.enable_debug}")
    print()

if __name__ == "__main__":
    # Validate and print configuration
    issues = validate_configuration()
    
    if issues:
        print("❌ Configuration Issues:")
        for issue in issues:
            print(f"   • {issue}")
    else:
        print("✅ Configuration validated successfully")
    
    print_configuration()
