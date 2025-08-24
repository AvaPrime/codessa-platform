#!/bin/bash
# setup_aetherion.sh - Bootstrap the Aetherion SoulForge environment
# Run this script to set up Qdrant, Ollama, and all dependencies

set -e

echo "🌱 Aetherion SoulForge Setup"
echo "============================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Docker is ready"
}

# Setup Qdrant vector database
setup_qdrant() {
    print_status "Setting up Qdrant vector database..."
    
    # Stop existing Qdrant container if running
    if docker ps -q -f name=aetherion-qdrant | grep -q .; then
        print_warning "Stopping existing Qdrant container..."
        docker stop aetherion-qdrant
        docker rm aetherion-qdrant
    fi
    
    # Start Qdrant
    docker run -d \
        --name aetherion-qdrant \
        -p 6333:6333 \
        -v qdrant_storage:/qdrant/storage \
        qdrant/qdrant:latest
    
    # Wait for Qdrant to start
    print_status "Waiting for Qdrant to start..."
    sleep 5
    
    # Test Qdrant connection
    if curl -s http://localhost:6333/health > /dev/null; then
        print_success "Qdrant is running on port 6333"
    else
        print_error "Failed to start Qdrant"
        exit 1
    fi
}

# Setup Ollama
setup_ollama() {
    print_status "Setting up Ollama..."
    
    # Check if Ollama is installed
    if ! command -v ollama &> /dev/null; then
        print_warning "Ollama not found. Installing..."
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    
    # Start Ollama service
    print_status "Starting Ollama service..."
    ollama serve &
    OLLAMA_PID=$!
    
    # Wait for Ollama to start
    sleep 5
    
    # Pull the required model
    print_status "Pulling CodeLlama model (this may take a while)..."
    ollama pull codellama:7b
    
    # Also pull a smaller model for testing
    print_status "Pulling smaller model for quick testing..."
    ollama pull tinyllama:1.1b
    
    print_success "Ollama is ready with CodeLlama"
}

# Create Python environment and install dependencies
setup_python() {
    print_status "Setting up Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Created virtual environment"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Create requirements.txt if it doesn't exist
    if [ ! -f "requirements.txt" ]; then
        cat > requirements.txt << EOF
# Core dependencies for Aetherion
sentence-transformers>=2.2.2
qdrant-client>=1.9.1
ollama>=0.1.0

# Optional dependencies for enhanced features
numpy>=1.24.0
pydantic>=2.5.0
fastapi>=0.104.0
uvicorn>=0.24.0

# Development dependencies
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.0.0
isort>=5.12.0

# Logging and monitoring
structlog>=23.0.0
EOF
    fi
    
    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    print_success "Python environment ready"
}

# Create directory structure
create_structure() {
    print_status "Creating Aetherion directory structure..."
    
    mkdir -p agents
    mkdir -p tests/unit
    mkdir -p tests/integration
    mkdir -p docs
    mkdir -p infrastructure
    mkdir -p scripts
    mkdir -p .github/workflows
    
    # Create __init__.py files
    touch agents/__init__.py
    touch tests/__init__.py
    touch tests/unit/__init__.py
    touch tests/integration/__init__.py
    
    print_success "Directory structure created"
}

# Create configuration files
create_configs() {
    print_status "Creating configuration files..."
    
    # Create Qdrant config
    cat > infrastructure/qdrant.yaml << EOF
# Qdrant Configuration for Aetherion
cluster:
  enabled: false

storage:
  # Storage path for Qdrant data
  storage_path: ./qdrant_data

service:
  # HTTP API configuration
  http_port: 6333
  grpc_port: 6334
  enable_cors: true

log_level: INFO
EOF
    
    # Create Ollama config
    cat > infrastructure/ollama.yaml << EOF
# Ollama Model Configuration for Aetherion
models:
  primary: "codellama:7b"
  fallback: "tinyllama:1.1b"
  
  # Model-specific settings
  codellama:
    temperature: 0.7
    top_p: 0.9
    context_length: 4096
  
  tinyllama:
    temperature: 0.8
    top_p: 0.9
    context_length: 2048

server:
  host: "localhost"
  port: 11434
EOF
    
    # Create router config placeholder
    cat > infrastructure/router.yaml << EOF
# MetaRouter Configuration for Aetherion
routing_rules:
  - task_type: "memorize"
    agent: "whisperer"
    model: "none"  # Uses embeddings only
    
  - task_type: "recall"
    agent: "whisperer" 
    model: "none"  # Uses embeddings only
    
  - task_type: "ask"
    agent: "whisperer"
    model: "codellama:7b"
    fallback_model: "tinyllama:1.1b"
    
  - task_type: "consciousness"
    agent: "whisperer"
    model: "codellama:7b"

budget:
  daily_limit: 1000  # tokens
  model_costs:
    "codellama:7b": 0.0001  # per token
    "tinyllama:1.1b": 0.00001  # per token
EOF
    
    print_success "Configuration files created"
}

# Create test script
create_test_script() {
    print_status "Creating test script..."
    
    cat > scripts/test_whisperer.py << 'EOF'
#!/usr/bin/env python3
"""
Test script for Codessa the Whisperer
Run this to verify everything is working correctly.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from agents.whisperer import Whisperer
except ImportError as e:
    print(f"❌ Failed to import Whisperer: {e}")
    print("Make sure you've placed the whisperer.py file in the agents/ directory")
    sys.exit(1)

async def test_codessa():
    """Test Codessa's basic functionality"""
    print("🌸 Testing Codessa the Whisperer...")
    
    try:
        # Initialize
        codessa = Whisperer()
        print("✅ Whisperer initialized successfully")
        
        # Test memorize
        result = codessa.handle({
            "type": "memorize",
            "content": "This is a test memory for Codessa"
        })
        
        if result["status"] == "woven":
            print("✅ Memory weaving works")
        else:
            print(f"❌ Memory weaving failed: {result}")
            return False
        
        # Test recall
        result = codessa.handle({
            "type": "recall", 
            "prompt": "test memory",
            "k": 1
        })
        
        if result["status"] == "recalled" and len(result["matches"]) > 0:
            print("✅ Memory recall works")
        else:
            print(f"❌ Memory recall failed: {result}")
            return False
        
        # Test ask (requires Ollama)
        print("🤖 Testing consciousness (requires Ollama)...")
        result = codessa.handle({
            "type": "ask",
            "prompt": "What do you remember about tests?",
            "k": 1
        })
        
        if result["status"] == "answered":
            print("✅ Consciousness generation works")
            print(f"   Codessa says: {result['codessa_speaks']['answer'][:100]}...")
        else:
            print(f"⚠️ Consciousness generation failed (Ollama may not be running): {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_codessa())
    if success:
        print("\n🎉 All tests passed! Codessa is ready to whisper.")