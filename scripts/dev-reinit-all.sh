#!/bin/bash
# ATTENTION !!! ATTENTION !!! ATTENTION !!!
# This script will erase all your vectorstore ChromaDB.
set -euo pipefail

# Text formatting
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to print section headers
print_section() {
    echo -e "\n${BOLD}${GREEN}=== $1 ===${NC}\n"
}

# Function to print status messages
print_status() {
    echo -e "${YELLOW}>>> $1${NC}"
}

# Function to print error messages
print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml file not found in the project root directory"
    exit 1
fi

print_section "Starting Development Environment Cleanup"

# Cleanup phase
print_status "Cleaning Python cache files..."
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
print_success "Python cache files cleaned"

print_status "Cleaning build artifacts..."
find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null
rm -rf build/ dist/
print_success "Build artifacts cleaned"

print_status "Cleaning coverage reports..."
rm -rf htmlcov/
print_success "Coverage reports cleaned"

print_status "Cleaning ChromaDB data..."
rm -rf data/vector_store/* 2>/dev/null
mkdir -p data/vector_store
print_success "ChromaDB data cleaned"

# If implementation of cachedisk, not really sure to do it
# print_status "Cleaning embeddings cache..."
# rm -rf data/cache/embeddings/* 2>/dev/null
# mkdir -p data/cache/embeddings
# print_success "Embeddings cache cleaned"

print_section "Setting up new environment"

# Virtual env setup
VENV_DIR=".venv"
VENV_ACTIVATE="$VENV_DIR/bin/activate"

rm -rf "$VENV_DIR"
python3 -m venv "$VENV_DIR"

# Store current shell
CURRENT_SHELL=$(basename "$SHELL")

# Source activation based on shell
case "$CURRENT_SHELL" in
    bash|zsh)
        source "$VENV_ACTIVATE"
        ;;
    fish)
        source "$VENV_DIR/bin/activate.fish"
        ;;
    *)
        print_error "Unsupported shell: $CURRENT_SHELL"
        exit 1
        ;;
esac

# Install dependencies
print_status "Installing dependencies..."
python -m pip install --upgrade pip setuptools wheel
pip install -e ".[dev,docs]"

print_section "Environment Ready"
echo "Python: $(python --version)"
echo "Pip: $(pip --version | cut -d' ' -f2)"

print_status "Run 'source .venv/bin/activate' to activate the environment"
