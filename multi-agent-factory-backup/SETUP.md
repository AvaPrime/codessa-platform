# Multi-Agent Factory Development Setup

## Quick Start (Recommended: uv workflow)

### 1. Install uv (fast Python package manager)
```bash
pip install uv
```

### 2. Create and activate virtual environment
```bash
# Create venv
uv venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Unix/macOS)
source .venv/bin/activate
```

### 3. Install dependencies
```bash
# Runtime + dev dependencies (default)
uv pip install -e .

# Add test dependencies
uv pip install -e ".[test]"

# Or install everything at once
uv pip install -e ".[dev,test]"
```

### 4. Verify installation
```bash
python -c "import fastapi; print('✅ Setup successful!')"
```

## Alternative: Standard pip workflow

```bash
# Create venv
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Unix

# Install dependencies
pip install -e ".[dev,test]"
```

## Makefile shortcuts

```bash
# Complete setup
make setup

# Individual installs
make install      # Production only
make install-dev  # + Development tools
make install-test # + Test dependencies
make install-all  # Everything

# Generate lockfiles
make lock
```

## Container Development

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or use the Makefile
make up
```