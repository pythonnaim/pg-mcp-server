FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories if they don't exist
RUN mkdir -p server extension_context

# Copy server code - use conditional copy to handle missing directories
COPY server ./server || true
COPY extension_context ./extension_context || true

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "-m", "server.app"]
