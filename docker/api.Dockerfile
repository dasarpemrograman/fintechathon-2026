FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
WORKDIR /app
RUN --mount=type=secret,id=cloud_ca if [ -s /run/secrets/cloud_ca ]; then cp /run/secrets/cloud_ca /usr/local/share/ca-certificates/environment-proxy-ca.crt && update-ca-certificates; fi && apt-get update && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils git && rm -rf /var/lib/apt/lists/*
COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt
ENV PYTHONUNBUFFERED=1 FINCATHON_TESSDATA_PATH=/opt/fincathon/tessdata
COPY scripts/install_ocr.py ./scripts/install_ocr.py
COPY fixtures/demo/ocr-assets.lock.json ./fixtures/demo/ocr-assets.lock.json
RUN python scripts/install_ocr.py
COPY . .
CMD ["python","-m","uvicorn","services.api.app:app","--host","0.0.0.0","--port","8000"]
