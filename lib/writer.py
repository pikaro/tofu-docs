"""Writer for the target file."""

import logging
import os
import re
import sys
from difflib import unified_diff
from pathlib import Path

import git

from lib.common.helper import if_index, marker
from lib.models.config import settings

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
        if settings.target_config.insert_position == 'bottom':
            return [*content, start_marker, *docs.splitlines(), end_marker]
        _err = 'Invalid insert position'
        raise ValueError(_err)

    if start == -1 or end == -1 or start > end:
        _err = 'Invalid marker positions in target'
        raise ValueError(_err)

    return content[: start + 1] + docs.splitlines() + content[end:]


class NotAFileException(Exception):  # noqa: N818 # not an error
    """Raised when the target is not a file."""


class Writer:
    """Writes the generated documentation to the target file."""

    _target: Path
    _generated_doc: str
    _changed: bool
    _original_content: str | None
    _updated_content: str | None

    def __init__(self, content: str) -> None:
        """Initialize the Writer class."""
        self._generated_doc = content
        self._updated_content = None
        self._changed = False

        if _is_stdout_target(settings.target):
            log.info('Writing to stdout')
            print(content)
            _err = 'Target is stdout'
            raise NotAFileException(_err)

        if _is_stderr_target(settings.target):
            log.info('Writing to stderr')
            print(content, file=sys.stderr)
            _err = 'Target is stderr'
            raise NotAFileException(_err)

        target = Path(settings.target)
        default_target = settings.__class__.__pydantic_fields__['target'].default
        if not target.is_absolute() and not re.match(r'^\.\.?/', settings.target):
            target = settings.module_path / settings.target
            if settings.target != default_target:
                log.warning(f'Target path {settings.target} is not relative, using {target}')
        target = target.resolve()

        log.info(f'Writing to {target}')

        if not target.exists():
            log.info(f'Creating {target}')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
            template = settings.target_config.empty_header.format(module=target.stem)
            _ = target.write_text(template, encoding='utf-8')
            self._changed = True
            self._original_content = None

        self._target = target

    def write(self):
        """Write the generated documentation to the target file."""
        self._original_content = self._target.read_text()
        lines = self._original_content.splitlines()
        try:
            updated_lines = _insert_marked_block(lines, self._generated_doc)
        except ValueError:
            log.exception('Error inserting marked block')
            raise

        self._updated_content = '\n'.join(updated_lines).strip() + '\n'

        self._changed = self._original_content != self._updated_content

        if self._changed:
            log.info(f'Updated {self._target} with {len(self._generated_doc.splitlines())} lines')
            _ = self._target.write_text(self._updated_content, encoding='utf-8')

    @property
    def changed(self) -> bool:
        """Check if the target file was changed."""
        return self._changed

    def diff(self):
        """Show the diff between the original and updated content."""
        if self._changed and self._original_content and self._updated_content:
            log.warning('Documentation was changed')

            if settings.debug:
                diff = unified_diff(
                    self._original_content.splitlines(),
                    self._updated_content.splitlines(),
                    lineterm='',
                )
                log.debug(f'Diff for {settings.module_path / settings.target}:')
                print('\n    '.join(diff))
        elif not self._original_content:
            log.warning('File was created')

    def git_add(self) -> None:
        """Add the target file to git."""
        log.info(f'Adding {self._target} to git')

        git.refresh(settings.git_executable)
        log.debug(f'Using git executable: {settings.git_executable}')

        repo = git.Repo(self._target, search_parent_directories=True)
        log.debug(f'Found git repository at {repo.working_tree_dir}')
        repo_root = repo.working_tree_dir
        if repo_root is None:
            _err = 'Could not locate git repository'
            raise RuntimeError(_err)
        target_relative = self._target.relative_to(repo_root)
        log.debug(f'Adding {target_relative} to git')
        repo.git.add(target_relative)
