FROM python:3.7-alpine
RUN apk add --no-cache git

WORKDIR /version-update

COPY /requirements.txt .

RUN pip install -r requirements.txt

COPY /version-update.py .

CMD ["python", "/version-update.py"]
