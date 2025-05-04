"""Formatter for formattable models."""

import logging
import re
from typing import TYPE_CHECKING, Generic, TypeVar

import tabulate

from lib.common.helper import if_index
from lib.models.input import ParsedHclItem
from lib.models.output import get_output_model
from lib.settings import settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from lib.types import OutputFormat

FormattableT = TypeVar('FormattableT', bound=ParsedHclItem)

log = logging.getLogger(__name__)

RE_BR = re.compile(r'(^(\s*<br/>\s*)+|(\s*<br/>\s*)+$)')


def _collapse_column(table: list[list[str]], column: str, keep_first_line: bool = False) -> None:
    """Collapse a column in the table."""
    idx = if_index(table[0], column)
    if idx != -1:
        for row in table[1:]:
            elem = row[idx]
            elem = RE_BR.sub('', elem)
            first = ''
            if keep_first_line:
                lines = elem.split('<br/>')
                first = lines[0].strip()
                elem = '<br/>'.join(lines[1:]).strip()
                elem = RE_BR.sub('', elem)
            if len(elem) > settings.config.format.collapsible_long_threshold:
                elem = f'<details>{elem}</details>'
            row[idx] = f'{first}<br/>{elem}' if keep_first_line else elem


class Formatter(Generic[FormattableT]):
    """Formatter for formattable models."""

    data: dict[str, FormattableT]
    skip_columns: set[str]

    def __init__(self, data: dict[str, FormattableT], skip_columns: set[str] | None = None) -> None:
        """Initialize the formatter."""
        self.data = data
        self.skip_columns = skip_columns or set()

    def format(self) -> str:
        """Format the data."""
        _formats: dict[OutputFormat, Callable[[], str]] = {
            'markdown': self._format_markdown,
        }

        if settings.config.target_config.format not in _formats:
            _err = f'Invalid format: {settings.config.target_config.format}'
            raise ValueError(_err)

        return _formats[settings.config.target_config.format]()

    def _make_table(self) -> list[list[str]]:
        item_name = next(iter(self.data))
        item = self.data[item_name]
        log.debug(f'Using {item_name} as the model')

        row_model = get_output_model(type(item))
        row_item = row_model(_data=item, _name=item_name, _module_root=settings.args.module_path)

        fields = row_item.model_dump().keys()

        header = [v.title() for v in fields if v not in self.skip_columns]

        rows = []
        for row_item_name, row_item in self.data.items():
            log.debug(f'Formatting {row_item_name}')
            formatted = row_model(
                _data=row_item, _name=row_item_name, _module_root=settings.args.module_path
            )
            rows.append([str(getattr(formatted, v)) for v in fields if v not in self.skip_columns])

        if settings.config.format.remove_empty_columns:
            columns = list(zip(*rows, strict=True))
            columns = [v for v in columns if any(v)]
            # FIXME: Unnecessary comprehension with str() due to return type
            rows = [[str(w) for w in v] for v in list(zip(*columns, strict=True))]

        if settings.config.format.sort_order == 'alpha-asc':
            rows.sort(key=lambda x: x[0])

        table = [header, *rows]

        if settings.config.format.collapsible_long_values:
            log.debug('Collapsing long values')
            _collapse_column(table, 'Value')

        if settings.config.format.collapsible_long_types:
            log.debug('Collapsing long types')
            _collapse_column(table, 'Type')

        if settings.config.format.collapsible_long_defaults:
            log.debug('Collapsing long defaults')
            _collapse_column(table, 'Default')

        if settings.config.format.collapsible_long_description:
            log.debug('Collapsing long descriptions')
            _collapse_column(table, 'Description', keep_first_line=True)

        return table

    def _format_markdown(self) -> str:
        """Format the data."""
        if not self.data:
            return ''

        table = self._make_table()
        table_text = tabulate.tabulate(table, headers='firstrow', tablefmt='github')
        table_text = re.sub(r'( )*\|( )*', r'\1|\2', table_text)
        table_text = re.sub(r'(?<=\|)-+(?=\|)', '---', table_text)

        return table_text  # noqa: RET504  # Unnecessary assignment - easier to expand

    def _format_html(self) -> str:
        """Format the data."""
        if not self.data:
            return ''

        table = self._make_table()
        table_text = tabulate.tabulate(table, headers='firstrow', tablefmt='html')

        return table_text  # noqa: RET504 # Unnecessary assignment - easier to expand
