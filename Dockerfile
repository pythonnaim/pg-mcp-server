# # Dockerfile
# FROM python:3.13-slim

# # The installer requires curl (and certificates) to download the release archive
# RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

# # Download the latest uv installer
# ADD https://astral.sh/uv/install.sh /uv-installer.sh

# # Run the installer then remove it
# RUN sh /uv-installer.sh && rm /uv-installer.sh

# # Ensure the installed binary is on the `PATH`
# ENV PATH="/root/.local/bin/:$PATH"

# # Copy the project into the image
# ADD . /app

# # Sync the project into a new environment, using the frozen lockfile
# WORKDIR /app
# RUN uv sync --frozen

# # Run the application
# CMD ["uv", "run", "-m", "server.app"]


FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server ./server
COPY extension_context ./extension_context

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "-m", "server.app"]
