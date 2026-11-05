# --- Stage 1: Build Next.js Web Console & Staff Portal ---
FROM node:20-alpine AS frontend-builder
WORKDIR /web

# Install dependencies
COPY web/package.json web/package-lock.json* ./
RUN npm ci

# Copy web source and build static export into web/out
COPY web/ ./
RUN npm run build

# --- Stage 2: Production Python Backend ---
FROM python:3.12-slim AS runner

WORKDIR /app

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy python requirements and install
COPY requirements.txt ./
RUN uv pip install --system -r requirements.txt

# Copy backend source code
COPY src/bytevoice/ ./src/bytevoice/
COPY scripts/ ./scripts/
COPY main.py ./

# Copy built frontend static export from Stage 1
COPY --from=frontend-builder /web/out ./web/out

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PORT=8000
ENV BYTEVOICE_WEB_DIR=/app/web/out

EXPOSE 8000

# Start FastAPI with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

