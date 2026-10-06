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
# The same release from several sources: ftp.gnu.org alone was unreachable during a deploy
# (2026-10-06). Every copy must match this checksum (identical on all sources, checked by hand).
ARG LIBREDWG_SHA256=62ebb73b984f865960f20ed26619ea5f8789d5e3fd088fa40a2598384da81275
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential pkg-config curl ca-certificates xz-utils \
    && rm -rf /var/lib/apt/lists/*
RUN set -e; f="/tmp/libredwg.tar.xz"; ok=""; \
    for url in \
        "https://ftp.gnu.org/gnu/libredwg/libredwg-${LIBREDWG_VERSION}.tar.xz" \
        "https://mirrors.kernel.org/gnu/libredwg/libredwg-${LIBREDWG_VERSION}.tar.xz" \
        "https://github.com/LibreDWG/libredwg/releases/download/${LIBREDWG_VERSION}/libredwg-${LIBREDWG_VERSION}.tar.xz" \
        "https://ftp.halifax.rwth-aachen.de/gnu/libredwg/libredwg-${LIBREDWG_VERSION}.tar.xz"; do \
      if curl -fsSL --retry 3 --retry-delay 5 --connect-timeout 20 -o "$f" "$url" \
         && echo "${LIBREDWG_SHA256}  $f" | sha256sum -c -; then ok=1; echo "libredwg from $url"; break; fi; \
      echo "libredwg: $url failed, trying the next source"; \
    done; \
    test -n "$ok"; \
    tar -xJf "$f" -C /tmp \
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
