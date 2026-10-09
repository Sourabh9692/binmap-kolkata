FROM node:24-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim
WORKDIR /app
RUN groupadd -g 10001 binmap && useradd -u 10001 -g binmap -m binmap
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY scripts/ scripts/
COPY --from=frontend /app/frontend/dist frontend/dist
RUN mkdir -p /app/data && chown -R binmap:binmap /app/data
ENV PYTHONPATH=/app/backend
USER binmap
EXPOSE 8000
CMD ["uvicorn","binmap.main:app","--host","0.0.0.0","--port","8000"]
