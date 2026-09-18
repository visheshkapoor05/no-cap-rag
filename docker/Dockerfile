# The office building itself: assembled once, then reused for every day it's open.
FROM python:3.12-slim

WORKDIR /app

# poppler-utils provides the `pdftotext` binary the ingestion mailroom
# (app/ingestion/extract.py) shells out to for PDF text extraction — it's
# a system package, not a pip package, so it has to be installed here or
# every PDF in the corpus fails ingestion with a "command not found" the
# unit tests (run on a dev machine that already has it) would never catch.
RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Office workflow: install the standing equipment (dependencies) before any
# staff show up (application code). Docker's layer cache skips this step
# entirely on the next build unless requirements.txt itself changed, so a
# plain code edit doesn't force a full dependency reinstall.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
