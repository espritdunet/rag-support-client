# Development Quick Start Guide

A comprehensive guide for developers working on the RAG Support Client project.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Development Workflow](#development-workflow)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Documentation](#documentation)
- [Dependency Management](#dependency-management)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.11 or higher
- Git
- Ollama 0.5.1 or higher
- ChromaDB prerequisites
- Poetry (recommended) or pip

## Initial Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/espritdunet/rag-support-client
   cd rag-support-client
   ```

2. **Environment Setup**
   ```bash
   # Create and activate virtual environment
   python -m venv .venv
   source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

   # Update core tools
   python -m pip install --upgrade pip setuptools wheel

   # Install project with all development dependencies
   pip install -e ".[dev,docs]"
   ```

3. **Configure Environment**
   ```bash
   # Copy example environment file
   cp .env.example .env

   # Edit .env with your settings
   # Required settings:
   # - OLLAMA_BASE_URL
   # - API_KEY
   # - CHROMA_PERSIST_DIRECTORY
   ```

## Development Workflow

### Maintenance Scripts

The project includes two important maintenance scripts in the `scripts/` directory:

1. **dev-reinit.sh**: Soft reset script
   - Cleans Python cache files and build artifacts
   - Preserves existing vector store data
   - Recreates virtual environment
   - Reinstalls dependencies
   ```bash
   ./scripts/dev-reinit.sh
   ```

2. **dev-reinit-all.sh**: Complete reset script
   - ⚠️ WARNING: This script will erase your vectorstore ChromaDB!
   - Performs complete cleanup including vector store
   - Recreates all directories
   - Reinstalls fresh environment
   ```bash
   ./scripts/dev-reinit-all.sh
   ```

Both scripts will:
- Check for pyproject.toml
- Clean Python cache files and build artifacts
- Set up a new virtual environment
- Support bash, zsh, and fish shells
- Install all development dependencies
- Display environment information

Use `dev-reinit.sh` for routine maintenance and `dev-reinit-all.sh` when you need a complete reset.

### Daily Development Setup

```bash
# Clean Python cache and build artifacts
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete
find . -name "*.egg-info" -type d -exec rm -rf {} +
rm -rf build/ dist/

# Verify installation
python -c "import rag_support_client; print(rag_support_client.__file__)"
```

### Running Development Servers

1. **Start the FastAPI Server**
   ```bash
   # Terminal 1
   python main.py
   ```

2. **Start the Streamlit UI**
   ```bash
   # Terminal 2
   streamlit run src/rag_support_client/streamlit/app.py
   ```

3. **Watch for Changes (Optional)**
   ```bash
   # Terminal 3
   watchmedo auto-restart -d src/ -p "*.py" -- streamlit run src/rag_support_client/streamlit/app.py
   ```

## Project Structure

```
src/rag_support_client/
├── api/                 # FastAPI routes and models
│   ├── routers/        # API endpoint definitions
│   └── models/         # Pydantic models
├── config/             # Application configuration
├── rag/                # Core RAG functionality
│   ├── embeddings/     # Vector embeddings
│   ├── llm/           # Ollama integration
│   └── processors/    # Document processing
├── streamlit/          # UI components
│   ├── pages/         # Streamlit pages
│   └── components/    # Reusable UI components
└── utils/             # Shared utilities
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_rag_chain.py -v

# Run tests in parallel
pytest -n auto
```

### Writing Tests

- Place tests in `tests/` directory
- Match source file structure
- Use fixtures for common setup
- Include both unit and integration tests

## Code Quality

### Running Quality Checks

```bash
# Format code
black .
isort .

# Lint code
ruff check .

# Type checking
mypy .
```

### Pre-commit Checks

```bash
# Before committing:
1. black .          # Format code
2. isort .         # Sort imports
3. ruff check .    # Lint
4. mypy .          # Type check
5. pytest          # Run tests
```

## Documentation

### Building Documentation

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build documentation
cd docs
make html
```

### Writing Documentation

- Use Google-style docstrings
- Update README.md for major changes
- Document public APIs
- Include code examples
- Keep architecture docs current

## Dependency Management

### Main Dependencies
- langchain==0.3.9
- chromadb==0.5.16
- fastapi>=0.115.4
- streamlit>=1.4.0

### Development Dependencies
- pytest>=8.3.3
- black>=24.2.0
- mypy>=1.8.0
- ruff>=0.3.0

### Adding Dependencies

1. Add to `pyproject.toml`
2. Specify version constraints
3. Update documentation
4. Test compatibility

## Troubleshooting

### Common Issues

1. **Environment Issues**
   ```bash
   # For routine cleanup while preserving vector store:
   ./scripts/dev-reinit.sh

   # For complete reset including vector store:
   ./scripts/dev-reinit-all.sh
   ```

2. **ChromaDB Issues**
   ```bash
   # Clear ChromaDB storage
   rm -rf chroma_db/
   ```

2. **Package Installation Issues**
   ```bash
   # Clear pip cache
   pip cache purge

   # Verify installation
   pip show rag-support-client
   ```

3. **Import Issues**
   ```bash
   # Check Python path
   python -c "import sys; print('\n'.join(sys.path))"
   ```

### Best Practices

1. Always use virtual environments
2. Clean cache when switching branches
3. Run full test suite before commits
4. Keep dependencies updated
5. Use development installation

## Deployment

### Building Package

```bash
# Clean previous builds
rm -rf build/ dist/

# Build package
python -m build

# Create wheel
python setup.py bdist_wheel
```

### Local Testing

```bash
# Install in a clean environment
pip install dist/rag_support_client-*.whl

# Verify installation
python -c "import rag_support_client"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Run all checks
5. Submit pull request

## Version Control

### Branch Strategy

- main: Production-ready code
- develop: Integration branch
- feature/*: New features
- bugfix/*: Bug fixes

### Commit Messages

Follow conventional commits:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- style: Formatting
- refactor: Code restructuring
- test: Adding tests
- chore: Maintenance

## Resources

- [Project Repository](https://github.com/espritdunet/rag-support-client)
# - [Documentation](https://rag-support-client.readthedocs.io/) - Not yet ¯\_(ツ)_/¯
- [Issue Tracker](https://github.com/espritdunet/rag-support-client/issues)