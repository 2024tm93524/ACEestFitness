# ─────────────────────────────────────────────
# Stage 1 – Base image
# ─────────────────────────────────────────────
FROM python:3.11-slim

# Metadata
LABEL maintainer="ACEest DevOps Team"
LABEL description="ACEest Fitness & Gym – Flask Application"

# Set working directory inside the container
WORKDIR /app

# Copy dependency list first (helps Docker cache layers)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source code
COPY . .

# Expose the port Flask will listen on
EXPOSE 5000

# Environment variables (can be overridden at runtime)
ENV FLASK_ENV=production
ENV DB_PATH=/app/aceest_fitness.db

# Initialize database and start the Flask app
CMD ["sh", "-c", "python -c 'from app import init_db; init_db()' && python app.py"]
