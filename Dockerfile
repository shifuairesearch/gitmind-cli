FROM node:22-bookworm-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.9.27@sha256:143b40f4ab56a780f43377604702107b5a35f83a4453daf1e4be691358718a6a /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /usr/local/lib/gitmind
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable --python /usr/bin/python3

FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/gitmind/.venv /usr/local/lib/gitmind/.venv
RUN ln -s /usr/local/lib/gitmind/.venv/bin/gitmind /usr/local/bin/gitmind
COPY smoke.py /usr/local/lib/gitmind/smoke.py
RUN --network=none python3 /usr/local/lib/gitmind/smoke.py
ENTRYPOINT ["gitmind"]
