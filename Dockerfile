FROM python:3.10-slim
COPY . /bolt/
RUN pip install -r /bolt/requirements.txt