"""Writer for the target file."""

import logging
import sys
from pathlib import Path

from lib.common.helper import if_index, marker
from lib.models.writer import WriterResult
from lib.settings import settings

log = logging.getLogger(__name__)


def _is_stdout_target(target: str) -> bool:
    """Check if the target is stdout."""
    return target in ['-', 'stdout', '/dev/stdout', '/dev/fd/1', '/proc/self/fd/1']


def _is_stderr_target(target: str) -> bool:
    """Check if the target is stderr."""
    return target in ['stderr', '/dev/stderr', '/dev/fd/2', '/proc/self/fd/2']


def _insert_marked_block(content: list[str], docs: str) -> list[str]:
    """Insert the generated documentation into the target file."""
    start_marker = marker('START')
    end_marker = marker('END')

    start = if_index(content, start_marker)
    end = if_index(content, end_marker)

    if start == -1 and end == -1:
        if settings.config.target_config.insert_position == 'bottom':
            return [*content, start_marker, *docs.splitlines(), end_marker]
        _err = 'Invalid insert position'
        raise ValueError(_err)

    if start == -1 or end == -1 or start > end:
        _err = 'Invalid marker positions in target'
        raise ValueError(_err)

    return content[: start + 1] + docs.splitlines() + content[end:]


class Writer:
    """Writes the generated documentation to the target file."""

    def write(self, content: str) -> WriterResult:
        """Write the generated documentation to the target file."""
        changed = False
        target = settings.args.module_path / settings.config.target

        if isinstance(target, str):
            target = Path(target)

        if _is_stdout_target(str(target)):
            log.info('Writing to stdout')
            print(content)
            return WriterResult(changed=changed, content=content, original_content=None)

        if _is_stderr_target(str(target)):
            log.info('Writing to stderr')
            print(content, file=sys.stderr)
            return WriterResult(changed=changed, content=content, original_content=None)

        log.info(f'Writing to {target}')

        if not target.exists():
            changed = True
            log.info(f'Creating {target}')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
            template = settings.config.target_config.empty_header.format(module=target.stem)
            _ = target.write_text(template)

        original_content = target.read_text()
        lines = original_content.splitlines()
        try:
            updated_lines = _insert_marked_block(lines, content)
        except ValueError:
            log.exception('Error inserting marked block')
            raise

        updated_content = '\n'.join(updated_lines).strip()

        changed = original_content.strip() != updated_content

        if changed:
            log.info(f'Updated {target} with {len(content.splitlines())} lines')
            _ = target.write_text(updated_content)

        return WriterResult(
            changed=changed,
            content=updated_content,
            original_content=original_content,
        )
