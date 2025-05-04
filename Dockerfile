FROM python:3.13-alpine

ENV PYTHONPATH="/usr/local/lib/python3.13/site-packages"

WORKDIR /app

# FIXME: https://github.com/python/cpython/issues/120308
RUN --mount=type=bind,source=./pyproject.toml,target=/app/pyproject.toml \
    --mount=type=bind,source=./poetry.lock,target=/app/poetry.lock \
    python3 -m venv .venv && \
    source .venv/bin/activate && \
    pip install --no-cache-dir poetry && \
    poetry self add poetry-plugin-export && \
    poetry export -f requirements.txt --only main --no-interaction --no-ansi > requirements.txt && \
    deactivate && \
    rm -rf .venv && \
    pip install --no-cache-dir -r requirements.txt

COPY ./tofu-docs.py /app/tofu-docs.py
COPY ./lib /app/lib

ENV TOFU_DOCS_DEBUG=0
ENV TOFU_DOCS_TARGET=README.md

ENV TOFU_DOCS_FORMAT__ADD_OUTPUT_VALUE=0
ENV TOFU_DOCS_FORMAT__ADD_RESOURCE_IDENTIFIER=1

ENV TOFU_DOCS_FORMAT__COLLAPSIBLE_LONG_DEFAULTS=1
ENV TOFU_DOCS_FORMAT__COLLAPSIBLE_LONG_DESCRIPTION=1
ENV TOFU_DOCS_FORMAT__COLLAPSIBLE_LONG_THRESHOLD=25
ENV TOFU_DOCS_FORMAT__COLLAPSIBLE_LONG_TYPES=1
ENV TOFU_DOCS_FORMAT__COLLAPSIBLE_LONG_VALUES=1
ENV TOFU_DOCS_FORMAT__COLLAPSIBLE_SECTIONS=1

ENV TOFU_DOCS_FORMAT__INCLUDE_LOCALS=1
ENV TOFU_DOCS_FORMAT__INCLUDE_OUTPUTS=1
ENV TOFU_DOCS_FORMAT__INCLUDE_RESOURCES=1
ENV TOFU_DOCS_FORMAT__INCLUDE_VARIABLES=1

ENV TOFU_DOCS_FORMAT__REMOVE_EMPTY_COLUMNS=1
ENV TOFU_DOCS_FORMAT__REMOVE_VALIDATION=1
ENV TOFU_DOCS_FORMAT__REQUIRED_VARIABLES_FIRST=1
ENV TOFU_DOCS_FORMAT__SKIP_AUTO=1
ENV TOFU_DOCS_FORMAT__SORT_ORDER=alpha-asc

ENV TOFU_DOCS_TARGET_CONFIG__EMPTY_HEADER="# {module}\n\n## Description\n\n[tbd]\n\n## Usage\n\ntbd\n\n## Examples\n\ntbd\n\n## Notes\n\ntbd\n"
ENV TOFU_DOCS_TARGET_CONFIG__FORMAT=markdown
ENV TOFU_DOCS_TARGET_CONFIG__HEADING='API Documentation'
ENV TOFU_DOCS_TARGET_CONFIG__HEADING_LEVEL=2
ENV TOFU_DOCS_TARGET_CONFIG__INSERT_POSITION=bottom
ENV TOFU_DOCS_TARGET_CONFIG__MARKER=TOFU_DOCS

ENTRYPOINT ["/app/tofu-docs.py"]
CMD ["--module_path", "/module"]
