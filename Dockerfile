#############################################
# Stage 1: Builder - Install dependencies
#############################################
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build tools required for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list
COPY requirements.txt .

# Install Python dependencies to a custom folder
RUN pip install --prefix=/install -r requirements.txt


#############################################
# Stage 2: Runtime - Final lightweight image
#############################################
FROM python:3.11-slim

ENV TZ=UTC
WORKDIR /app

# Install cron + timezone data
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tzdata \
    && ln -sf /usr/share/zoneinfo/UTC /etc/localtime \
    && echo "UTC" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder stage
COPY --from=builder /install /usr/local

# Copy your application code
COPY app/ /app/app/
COPY scripts/ /app/scripts/
COPY cron/2fa-cron /etc/cron.d/2fa-cron

# Copy your RSA key files
COPY student_private.pem /app/student_private.pem
COPY student_public.pem /app/student_public.pem
COPY instructor_public.pem /app/instructor_public.pem

# Set correct permissions for cron file
RUN chmod 0644 /etc/cron.d/2fa-cron

# Register the cron job (strip the 'root' username for the user crontab)
RUN sed 's/root //' /etc/cron.d/2fa-cron | crontab -

# Create persistent storage directories
RUN mkdir -p /data && chmod 755 /data
RUN mkdir -p /cron && chmod 755 /cron

# Expose FastAPI port
EXPOSE 8080

# Start both cron service + FastAPI app
CMD cron && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080