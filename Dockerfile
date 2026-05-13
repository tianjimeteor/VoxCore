# syntax=docker/dockerfile:1.6
# Multi-stage build for VoxCore — produces a minimal, non-root runtime image.

FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Build wheel
COPY pyproject.toml README.md LICENSE ./
COPY voxcore ./voxcore
RUN pip install --upgrade pip build && \
    python -m build --wheel


FROM python:3.12-slim AS runtime

# Security: non-root user
RUN groupadd --system --gid 1001 voxcore && \
    useradd --system --uid 1001 --gid voxcore --home /app --shell /sbin/nologin voxcore

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VOXCORE_HOST=0.0.0.0 \
    VOXCORE_PORT=8000

WORKDIR /app

# Install wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

# Drop privileges
USER voxcore

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status==200 else 1)"

ENTRYPOINT ["voxcore"]
CMD ["run"]
