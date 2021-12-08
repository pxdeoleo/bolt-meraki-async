FROM python:3.10-slim
COPY . /bolt/
RUN pip install -r /src/bolt/requirements.txt