#!/usr/bin/env bash

# All fixtures and Git changes stay inside the disposable container.
set -euo pipefail

image="${1:-tofu-docs:test}"
docker run --rm --network none --user 0 --entrypoint /bin/sh "$image" -eu -c '
    mkdir /src
    git init -q /src
    printf "# Test module\n" > /src/README.md
    printf "variable \"name\" {\n  type = string\n  description = \"Test input\"\n}\n" > /src/main.tf
    printf "target_config:\n  heading: Container configuration test\n" > /src/.tofu-docs.yml
    chown -R 12345:12345 /src

    /app/tofu-docs.py --module-path=/src --config-file=/src/.tofu-docs.yml --changed-git-add
    test "$(git -C /src diff --cached --name-only)" = README.md
    grep -q "Container configuration test" /src/README.md

    mkdir /untrusted
    git init -q /untrusted
    chown -R 12345:12345 /untrusted
    if git -C /untrusted status --porcelain 2>/tmp/untrusted-error; then
        echo "FAIL: ownership checks were disabled outside /src" >&2
        exit 1
    fi
    case "$(cat /tmp/untrusted-error)" in
        *"dubious ownership"*) ;;
        *) cat /tmp/untrusted-error >&2; exit 1 ;;
    esac
    echo "PASS: README staged at /src; other ownership checks remain active"
'
