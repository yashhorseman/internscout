FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/tmp/huggingface

COPY requirements.txt requirements-rerank.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# --build-arg WITH_RERANK=1 adds the cross-encoder (CPU build of PyTorch). Used to measure it.
ARG WITH_RERANK=0
RUN if [ "$WITH_RERANK" = "1" ]; then \
      pip install --no-cache-dir torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu && \
      pip install --no-cache-dir -r requirements-rerank.txt; \
    fi

COPY app ./app
COPY migrations ./migrations

RUN useradd --system --uid 10001 internscout
USER internscout
EXPOSE 8000
# migrate first: a fresh database gets its tables; an up-to-date one is left alone
CMD ["sh", "-c", "python -m app.db migrate && exec uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
