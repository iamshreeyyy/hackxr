#!/bin/bash

# LLM Document Processing System Setup Script

echo "🚀 Setting up LLM Document Processing System..."

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_major=3
required_minor=8

version_major=$(echo $python_version | cut -d. -f1)
version_minor=$(echo $python_version | cut -d. -f2)

if [ "$version_major" -lt "$required_major" ] || ([ "$version_major" -eq "$required_major" ] && [ "$version_minor" -lt "$required_minor" ]); then
    echo "❌ Error: Python 3.8+ is required. You have Python $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cp env_example.txt .env
    echo "✅ .env file created. Please edit it with your configuration."
else
    echo "✅ .env file already exists"
fi

# Create logs directory
if [ ! -d "logs" ]; then
    echo "📁 Creating logs directory..."
    mkdir logs
    echo "✅ Logs directory created"
fi

# Create data directory for uploaded documents
if [ ! -d "data" ]; then
    echo "📁 Creating data directory..."
    mkdir data
    echo "✅ Data directory created"
fi

# Download spaCy model (optional)
echo "🔤 Downloading spaCy model (optional)..."
python -m spacy download en_core_web_sm 2>/dev/null || echo "⚠️  spaCy model download failed (optional feature)"

# Test the installation
echo "🧪 Testing installation..."
python -c "
try:
    import fastapi, uvicorn, pydantic, numpy, pandas
    from sentence_transformers import SentenceTransformer
    print('✅ Core dependencies imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

echo "🎉 Setup completed successfully!"
echo ""
echo "🏃 To start the system:"
echo "  1. Edit .env with your configuration"
echo "  2. Run: source venv/bin/activate"
echo "  3. Run: python main.py"
echo ""
echo "📖 API Documentation will be available at: http://localhost:8000/docs"
