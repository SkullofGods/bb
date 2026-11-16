# Explicit Python runtime for bothost: bot settings -> "Additional settings" ->
# enable the custom Dockerfile checkbox, then run a NEW DEPLOY (a restart is not enough).
# Without it the host's auto-detection may start this project with Node.js and fail
# with "window is not defined" or 'Unknown file extension ".py"'.
# Keep this file ASCII-only: bothost docs warn that non-ASCII comments can break the build.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Only needed for the optional bot (menu button). The web app itself has no deps.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The host passes the port in PORT and expects the app to listen on 0.0.0.0.
EXPOSE 3000
CMD ["python", "server.py"]
