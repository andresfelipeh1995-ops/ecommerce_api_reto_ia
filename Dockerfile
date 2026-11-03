# Dockerfile para la API FastAPI
# Imagen slim: suficiente para producción (sin toolchain de compilación)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1) Dependencias primero (aprovecha la caché de capas de Docker)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2) Código de la aplicación
COPY app ./app

# 3) Usuario no-root por seguridad
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Sondeo de salud: /health es público y no toca la BD
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
