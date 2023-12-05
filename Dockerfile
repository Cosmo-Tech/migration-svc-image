FROM python:3

# scripts
COPY . .
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "service.py"]