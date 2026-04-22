FROM python:3.12-slim

WORKDIR /app

# Copy requirements first (before other files)
COPY Progect8/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire Progect8 directory
COPY Progect8/ .

# Expose port
EXPOSE 5000

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "backend.app:app"]
