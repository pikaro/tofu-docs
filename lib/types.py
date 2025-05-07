"""Types."""

from typing import Literal

OutputFormat = Literal['markdown']
InsertPosition = Literal['bottom']
SortOrder = Literal['alpha-asc']
ValidationField = Literal['validation', 'precondition', 'postcondition']
ReplaceableField = Literal[
    'description', 'type', 'default', 'validation', 'value', 'precondition', 'postcondition'
]
