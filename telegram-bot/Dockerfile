FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Copy configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy application files (entry point and package)
COPY main.py ./
COPY bot/ ./bot/

# Sync project (creates .venv)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Runtime stage
FROM python:3.13-alpine

WORKDIR /app

# Copy the pre-built environment
COPY --from=builder /app/.venv /app/.venv

# Add virtualenv bin to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code (entry point and package)
COPY main.py ./
COPY bot/ ./bot/

CMD ["python", "main.py"]
