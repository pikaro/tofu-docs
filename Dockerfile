FROM python:3.13-alpine

ENV PYTHONPATH="/usr/local/lib/python3.13/site-packages"

WORKDIR /app

# FIXME: https://github.com/python/cpython/issues/120308

# Writing and reading from / to file in same pipeline -> false positive
# hadolint ignore=SC2094
RUN --mount=type=bind,source=./pyproject.toml,target=/app/pyproject.toml \
    --mount=type=bind,source=./poetry.lock,target=/app/poetry.lock \
    python3 -m venv .venv && \
    source .venv/bin/activate && \
    pip install --no-cache-dir 'poetry>=2.0,<3.0' && \
    poetry self add poetry-plugin-export && \
    poetry export -f requirements.txt --only main --no-interaction --no-ansi > requirements.txt && \
    deactivate && \
    rm -rf .venv && \
    pip install --no-cache-dir -r requirements.txt

COPY ./tofu-docs.py /app/tofu-docs.py
COPY ./lib /app/lib

ENV TOFU_DOCS_DEBUG=
ENV TOFU_DOCS_TARGET=
ENV TOFU_DOCS_CHANGED_EXIT_CODE=

ENV TOFU_DOCS_FORMAT__ADD_OUTPUT_VALUE=
ENV TOFU_DOCS_FORMAT__ADD_RESOURCE_IDENTIFIER=

ENV TOFU_DOCS_FORMAT__COLLAPSIBLE_LONG_DEFAULTS=
ENV TOFU_DOCS_FORMAT__COLLAPSIBLE_LONG_DESCRIPTION=
ENV TOFU_DOCS_FORMAT__COLLAPSIBLE_LONG_THRESHOLD=
ENV TOFU_DOCS_FORMAT__COLLAPSIBLE_LONG_TYPES=
ENV TOFU_DOCS_FORMAT__COLLAPSIBLE_LONG_VALUES=
ENV TOFU_DOCS_FORMAT__COLLAPSIBLE_SECTIONS=

ENV TOFU_DOCS_FORMAT__INCLUDE_LOCALS=
ENV TOFU_DOCS_FORMAT__INCLUDE_OUTPUTS=
ENV TOFU_DOCS_FORMAT__INCLUDE_RESOURCES=
ENV TOFU_DOCS_FORMAT__INCLUDE_VARIABLES=

ENV TOFU_DOCS_FORMAT__REMOVE_EMPTY_COLUMNS=
ENV TOFU_DOCS_FORMAT__VALIDATION_REMOVE=
ENV TOFU_DOCS_FORMAT__VALIDATION_SEPARATE=
ENV TOFU_DOCS_FORMAT__REQUIRED_VARIABLES_FIRST=
ENV TOFU_DOCS_FORMAT__SKIP_AUTO=
ENV TOFU_DOCS_FORMAT__SORT_ORDER=

ENV TOFU_DOCS_TARGET_CONFIG__EMPTY_HEADER=
ENV TOFU_DOCS_TARGET_CONFIG__FORMAT=
ENV TOFU_DOCS_TARGET_CONFIG__HEADING=
ENV TOFU_DOCS_TARGET_CONFIG__HEADING_LEVEL=
ENV TOFU_DOCS_TARGET_CONFIG__INSERT_POSITION=
ENV TOFU_DOCS_TARGET_CONFIG__MARKER=

ENTRYPOINT ["/app/tofu-docs.py"]
CMD ["--module_path", "/module"]
