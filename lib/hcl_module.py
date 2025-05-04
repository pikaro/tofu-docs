"""Represents an HCL (HashiCorp Configuration Language) codebase."""

import logging
from typing import TYPE_CHECKING

from lib.formatter import Formatter
from lib.hcl_file import HclFile
from lib.models.input import (
    HclLocalFields,
    HclOutputFields,
    HclResourceFields,
    HclVariableFields,
    ParsedHclItem,
)
from lib.settings import settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from lib.types import OutputFormat

log = logging.getLogger(__name__)


class HclModule:
    """Represents an HCL codebase."""

    data: list[HclFile]

    resource_flat: dict[str, ParsedHclItem[HclResourceFields]]
    locals: dict[str, ParsedHclItem[HclLocalFields]]
    variable: dict[str, ParsedHclItem[HclVariableFields]]
    output: dict[str, ParsedHclItem[HclOutputFields]]

    def __init__(self):
        """Initialize an OpenTofu module."""
        self.data = []

        for f in settings.args.module_path.glob('*.tf'):
            if f.is_file():
                if settings.config.format.skip_auto and f.name.startswith('auto.'):
                    log.info(f'Skipping auto-generated file: {f}')
                    continue
                self.data.append(HclFile(f))

        self.resource_flat = {}
        self.locals = {}
        self.variable = {}
        self.output = {}

        for f in self.data:

            def _add_kind(kind: str, allow_duplicates: bool = False, f=f) -> None:
                source_data = getattr(f, kind)
                data = getattr(self, kind)

                for k, v in source_data.items():
                    if k in data and not allow_duplicates:
                        _err = f'Already defined: {kind} {k}'
                        raise ValueError(_err)
                    data[k] = v

            _add_kind('locals')
            _add_kind('variable')
            _add_kind('output')
            allow_duplicates = not settings.config.format.add_resource_identifier
            _add_kind('resource_flat', allow_duplicates=allow_duplicates)

    def format(self) -> str:
        """Format the data."""
        _formats: dict[OutputFormat, Callable[[], str]] = {
            'markdown': self._format_markdown,
        }

        if settings.config.target_config.format not in _formats:
            _err = f'Invalid format: {settings.config.target_config.format}'
            raise ValueError(_err)

        return _formats[settings.config.target_config.format]()

    def _format_markdown(self) -> str:
        """Format the data as Markdown."""
        heading = settings.config.target_config.heading_level * '#'
        subheading = heading + '#'

        def _format(data: dict[str, ParsedHclItem], skip_columns: set[str] | None = None) -> str:
            formatter = Formatter(data, skip_columns=skip_columns)
            return formatter.format()

        def _format_section(
            section_name: str,
            data: dict[str, ParsedHclItem],
            skip_columns: set[str] | None = None,
        ) -> str:
            output = ''
            if settings.config.format.collapsible_sections:
                output += '<details>\n'
                output += f'<summary>{section_name}</summary>\n\n'
            output += f'{subheading} {section_name}\n\n'
            output += _format(data, skip_columns=skip_columns)
            if settings.config.format.collapsible_sections:
                output += '\n</details>\n'
            output += '\n\n'
            return output

        output = f'{heading} {settings.config.target_config.heading}\n\n'

        output += '<!-- markdownlint-disable -->\n'

        if settings.config.format.include_resources:
            output += _format_section('Resources', self.resource_flat)
        if settings.config.format.include_locals:
            output += _format_section('Locals', self.locals)

        if settings.config.format.include_variables:
            if settings.config.format.required_variables_first:
                data = {k: v for k, v in self.variable.items() if v.data.required}
                output += _format_section('Required Variables', data, skip_columns={'default'})
                data = {k: v for k, v in self.variable.items() if not v.data.required}
                output += _format_section('Optional Variables', data)
            else:
                output += _format_section('Variables', self.variable)

        if settings.config.format.include_outputs:
            skip_columns = None if settings.config.format.add_output_value else {'value'}
            output += _format_section('Outputs', self.output, skip_columns=skip_columns)

        output += '<!-- markdownlint-enable -->\n'

        return output
