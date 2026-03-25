# Use a lightweight Python 3.12 image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# 1. Copy BOTH package definitions FIRST (Crucial for Docker caching)
COPY requirements.txt .
COPY pyproject.toml .

# 2. Install dependencies (This will now successfully run the '-e .' command)
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the rest of the Origins Forge source code
COPY . .

# 4. Render injects the $PORT environment variable automatically.
# We must bind Uvicorn to 0.0.0.0 and use that dynamic port.
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-10000}
