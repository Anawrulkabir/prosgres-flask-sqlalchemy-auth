FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV FLASK_APP=app
ENV FLASK_ENV=production

EXPOSE 5001

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "app:create_app()"]
