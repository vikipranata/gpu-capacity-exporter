FROM python:3.9-slim

WORKDIR /src

# Install dependencies
COPY ./requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY ./app /src/app

# Expose port
EXPOSE 9100

# Run the application
CMD ["python", "/src/app/gpu_capacity_exporter.py"]