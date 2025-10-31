FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY ./app /app/app

# Expose port
EXPOSE 9100

# Run the application
CMD ["python", "./app/gpu_capacity_exporter.py"]