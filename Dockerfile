FROM python:3

# scripts
COPY common.py .
COPY kusto_test.py .
COPY kusto.py .
COPY requirements.txt .
COPY service.py .
COPY solution.py .
COPY storage.py .
RUN pip install -r requirements.txt

EXPOSE 8000

ENTRYPOINT ["python", "service.py"]