# User Quick Start Guide

## Introduction

RAG Support Client is a powerful tool that provides intelligent responses to your questions by using your Markdown documentation as a knowledge base. This guide will help you get started with both the web interface (Streamlit) and the API to connect a remote chatbot.

## Installation

### Prerequisites
- Python 3.11
- Ollama 0.5 installed and running locally
- Internet connection for initial setup

### Basic Setup

1. Install the package:
   ```bash
   pip install rag-support-client
   ```

2. Verify Ollama installation:
   ```bash
   ollama --version
   # Should show version 0.5 or higher
   ```

## Using the Web Interface

### Starting the Interface

1. Open a terminal and run:
   ```bash
   rag-support
   ```

2. Your default web browser will open automatically to `http://localhost:8501`

### Main Features

#### Chat Interface
1. Enter your question in the text input at the bottom
2. Click "Send" or press Enter
3. View the response with:
   - Step-by-step instructions
   - Relevant source links
   - Interface element references

#### Document Management (Admin)
1. Navigate to the Admin page
2. Upload new Markdown documents
3. View current document status
4. Manage document indexing

### Best Practices for Questions

DO:
- Be specific in your questions
- Include relevant technical terms
- Reference specific interfaces or features
- Ask one question at a time

DON'T:
- Ask multiple questions at once
- Use vague terms
- Skip technical terms
- Ask about information not in your docs

## Using the API

### Authentication

1. Get your API key from your administrator
2. Include it in all requests:
   ```bash
   X-API-Key: your-api-key
   ```

### Basic Endpoints

#### Create a Session
```bash
POST /api/v1/chat/session
```

#### Ask a Question
```bash
POST /api/v1/chat/{session_id}
Content-Type: application/json

{
    "question": "How do I configure the API key?"
}
```

#### End Session
```bash
DELETE /api/v1/chat/{session_id}
```

### Response Format

All responses follow this JSON structure:
```json
{
    "title": "Procedure Title",
    "steps": [
        {
            "step_number": 1,
            "description": "Step description",
            "interface_elements": ["Button name", "Menu item"]
        }
    ]
}
```

## Configuration

### Environment Variables

Key variables you might need to adjust:
- `OLLAMA_BASE_URL`: Location of your Ollama instance
- `API_KEY`: Your authentication key
- `DEBUG`: Enable/disable debug mode

### Application Settings for embeddings and LLM

Default settings can be adjusted in `.env`:
- Response length
- Search precision
- Number of sources
- Session timeout
- And more...

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify Ollama is running
   - Check your network connection
   - Confirm port settings

2. **Authentication Errors**
   - Verify API key is correct
   - Check key hasn't expired
   - Ensure proper header format

3. **No Response**
   - Check question length
   - Verify documentation is indexed
   - Check for system errors

### Getting Help

If you encounter any issues:

First Steps:

Check your internet connection
Verify that Ollama is running (ollama --version)
Try refreshing the web interface
Ensure your API key is valid (for API users)


Contact Support:

Open an issue on GitHub with a detailed description
Include the exact error message you received
Describe the steps to reproduce the issue
Specify which interface you're using (StreamLit Web UI or FastAPI API)
Include your Python and rag-support-client versions

## Best Practices

### Document Organization

1. Keep documentation updated
2. Use clear headings
3. Include source URLs in the last line of each document
4. Maintain consistent formatting

### Efficient Usage

1. Start with specific questions
2. Use technical terms
3. Review source links
4. Learn from responses

## FAQ

**Q: How long should I wait for responses?**
A: Typically 2-5 seconds. Longer questions or complex searches might take up to 10 seconds, depends of your Ollama server

**Q: Can I use the same session for multiple questions?**
A: Yes, sessions maintain context for up to 1 hour of inactivity.

**Q: How do I reset the context?**
A: Start a new session or click "Clear Chat" in the web interface.

**Q: Can I use markdown in my questions?**
A: No, questions should be plain text. The system will format responses appropriately.

## Security Notes

1. Never share your API key
2. Use HTTPS for production with a reverse proxy
3. Regular password updates
4. Monitor access logs

## Updates and Maintenance

### Staying Updated

1. Check for updates:
   ```bash
   pip install --upgrade rag-support-client
   ```

2. Review changelog for breaking changes

### Regular Maintenance

1. Update documentation
2. Clean up old sessions
3. Monitor system resources
4. Backup configurations

## Support Resources

- GitHub Issues: [Issue Tracker](https://github.com/espritdunet/rag-support-client/issues)
# - Documentation: [ReadTheDocs] - Not yet ¯\_(ツ)_/¯
# - Community: [Discord Channel] - Not yet ¯\_(ツ)_/¯
