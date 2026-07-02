FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
# Pre-install CPU-only torch (no CUDA, no torchaudio which causes version mismatch)
RUN pip install --no-cache-dir torch==2.5.1 torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

EXPOSE 5001

CMD ["python", "-u", "app.py"]
