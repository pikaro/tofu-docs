"""Represents an HCL (HashiCorp Configuration Language) codebase."""

import logging
from typing import TYPE_CHECKING

from lib.formatter import Formatter
from lib.hcl_file import HclFile
from lib.models.config import settings
from lib.models.input import (
    ParsedData,
    ParsedHclItem,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from lib.types import OutputFormat

log = logging.getLogger(__name__)


class HclModule:
    """Represents an HCL codebase."""

    _data: list[HclFile]
    _parsed_data: ParsedData

    def __init__(self):
        """Initialize an OpenTofu module."""
        self._data = []

        for f in settings.module_path.glob('*.tf'):
            if f.is_file():
                if settings.format.skip_auto and f.name.startswith('auto.'):
                    log.info(f'Skipping auto-generated file: {f}')
                    continue
                self._data.append(HclFile(f))

        self._parsed_data = ParsedData()

        for f in self._data:

            def _add_kind(kind: str, allow_duplicates: bool = False, f=f) -> None:
                source_data = getattr(f.get_parsed_data(), kind)
                data = getattr(self._parsed_data, kind)

                for k, v in source_data.items():
                    if k in data and not allow_duplicates:
                        _err = f'Already defined: {kind} {k}'
                        raise ValueError(_err)
                    data[k] = v

            _add_kind('locals')
            _add_kind('variable')
            _add_kind('output')
            _add_kind('validation')

            allow_duplicates = not settings.format.add_resource_identifier
            _add_kind('resource', allow_duplicates=allow_duplicates)

    def format(self) -> str:
        """Format the data."""
        _formats: dict[OutputFormat, Callable[[], str]] = {
            'markdown': self._format_markdown,
        }

        if settings.target_config.format not in _formats:
            _err = f'Invalid format: {settings.target_config.format}'
            raise ValueError(_err)

        return _formats[settings.target_config.format]()

    @staticmethod
    def _format_markdown_section(
        section_name: str,
        data: dict[str, ParsedHclItem],
        skip_columns: set[str] | None = None,
    ) -> str:
        if not data:
            return ''

        def _format(data: dict[str, ParsedHclItem], skip_columns: set[str] | None = None) -> str:
            formatter = Formatter(data, skip_columns=skip_columns)
            return formatter.format()

        heading = settings.target_config.heading_level * '#'
        subheading = heading + '#'
        output = ''
        if settings.format.collapsible_sections:
            output += '<details>\n'
            output += f'<summary>{section_name}</summary>\n\n'
        output += f'{subheading} {section_name}\n\n'
        output += _format(data, skip_columns=skip_columns)
        if settings.format.collapsible_sections:
            output += '\n</details>\n'
        output += '\n\n'
        return output

    def _format_markdown(self) -> str:
        """Format the data as Markdown."""
        heading = settings.target_config.heading_level * '#'

        output = f'{heading} {settings.target_config.heading}\n\n'

        output += '<!-- markdownlint-disable -->\n'

        if settings.format.include_resources:
            output += self._format_markdown_section('Resources', self._parsed_data.resource)
        if settings.format.include_locals:
            output += self._format_markdown_section('Locals', self._parsed_data.locals)

        if settings.format.include_variables:
            if settings.format.required_variables_first:
                data = {k: v for k, v in self._parsed_data.variable.items() if v.data.required}
                output += self._format_markdown_section(
                    'Required Variables', data, skip_columns={'default'}
                )
                data = {k: v for k, v in self._parsed_data.variable.items() if not v.data.required}
                output += self._format_markdown_section('Optional Variables', data)
            else:
                output += self._format_markdown_section('Variables', self._parsed_data.variable)

        if settings.format.include_outputs:
            skip_columns = None if settings.format.add_output_value else {'value'}
            output += self._format_markdown_section(
                'Outputs', self._parsed_data.output, skip_columns=skip_columns
            )
            output += self._format_markdown_section(
                'Validation', self._parsed_data.validation, skip_columns=skip_columns
            )

        output += '<!-- markdownlint-enable -->\n'

        return output
