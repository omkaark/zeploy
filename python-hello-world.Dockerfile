# File: python-hello-world.Dockerfile
FROM python:3.9-slim

# Create app directory
WORKDIR /app

# Create a Python file with a print statement
RUN echo 'print("Hello, World!")' > hello.py

# Run the Python script
CMD ["python", "hello.py"]