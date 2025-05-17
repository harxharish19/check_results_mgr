# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the 'api' directory contents into the container at /app/api
COPY api/ ./api/

# Make port 8000 available to the world outside this container (or your chosen APP_PORT)
EXPOSE 8001

# Define environment variables (these can be overridden in docker-compose.yml)
# Add placeholders for your actual credentials and settings
ENV SMTP_SERVER="smtp.gmail.com"
ENV SMTP_PORT=587
ENV SMTP_USERNAME="harxharish@gmail.com"
ENV SMTP_PASSWORD="HarisHBKAAAA1903@!"
ENV SENDER_EMAIL="harxharish@gmail.com"
ENV RECEIVER_EMAIL="harish@elevasionx.com"
ENV KV_URL="redis://redis:6379"
ENV APP_PORT=8001

# Run check_results.py when the container launches
CMD ["python", "api/check_results.py"]