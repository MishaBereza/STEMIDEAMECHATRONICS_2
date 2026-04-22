FROM python:3.12-slim

WORKDIR /app

# Copy the entire Progect8 directory
COPY Progect8/ .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 5000

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "60", "backend.app:app"]
