# One image, one service: the FastAPI backend serves the API and the built React app
# (same origin, no CORS). Deployed on Render from render.yaml; runs anywhere Docker runs.

# ---------- Stage 1: build the React frontend ----------
FROM node:20-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json* ./
RUN npm install
COPY vite.config.js index.html ./
COPY public ./public
COPY src ./src
RUN npm run build

# ---------- Stage 2: LibreDWG dwg2dxf (DWG uploads) ----------
# Debian no longer packages LibreDWG, so it is built from the GNU release — the same
# version used in development, so DWG conversion behaves identically online.
FROM python:3.12-slim AS libredwg
ARG LIBREDWG_VERSION=0.14
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential pkg-config curl ca-certificates xz-utils \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL "https://ftp.gnu.org/gnu/libredwg/libredwg-${LIBREDWG_VERSION}.tar.xz" | tar -xJ -C /tmp \
    && cd "/tmp/libredwg-${LIBREDWG_VERSION}" \
    && ./configure --prefix=/opt/libredwg --disable-shared --enable-static \
                   --disable-bindings --disable-docs \
    && make -j"$(nproc)" \
    && make install \
    && /opt/libredwg/bin/dwg2dxf --version

# ---------- Stage 3: Python backend serving API + built frontend ----------
FROM python:3.12-slim
WORKDIR /app
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=libredwg /opt/libredwg/bin/dwg2dxf /usr/local/bin/dwg2dxf
COPY api/ .
COPY --from=frontend /build/dist ./static
RUN mkdir -p /app/data

ENV PORT=8000 \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
