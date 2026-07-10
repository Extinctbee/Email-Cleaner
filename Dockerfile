FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY credentials.json .

EXPOSE 8501

CMD ["streamlit", "run", "src/GmailScript.py", "--server.port=8501", "--server.address=0.0.0.0"]
