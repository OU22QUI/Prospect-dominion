FROM python:3.11-slim

WORKDIR /app

COPY services/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY migrations /migrations
COPY services/migrations/apply.py ./apply.py

CMD ["python", "apply.py"]
