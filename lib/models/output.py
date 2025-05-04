"""Output models."""

import logging
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel, computed_field

from lib.common.formatter import format_description, format_validation
from lib.common.helper import find_prop_in_block
from lib.const import TERRAFORM_URL
from lib.models.input import (
    HclDataModel,
    HclLocalFields,
    HclOutputFields,
    HclResourceFields,
    HclVariableFields,
    ParsedHclItem,
)

RowT = TypeVar('RowT', bound=HclDataModel)


_registry: dict[type[HclDataModel], type['ItemRow']] = {}

log = logging.getLogger(__name__)


def register_model(input_model_cls):
    """Register an association between input and output models."""

    def decorator(output_model_cls):
        """Register a model with the registry."""
        _registry[input_model_cls] = output_model_cls
        log.debug(f'Registered {input_model_cls} -> {output_model_cls}')
        return output_model_cls

    return decorator


class ItemRow(BaseModel, Generic[RowT]):
    """Represents a row in the item table."""

    def __init__(self, _data: 'ParsedHclItem', _name: str, _module_root: Path, **kwargs):
        """Initialize the row."""
        super().__init__(**kwargs)
        self._data = _data
        self._name = _name
        self._module_root = _module_root

    _data: ParsedHclItem[RowT]
    _name: str
    _module_root: Path

    @computed_field()
    @property
    def name(self) -> str:
        """Return a link to the resource."""
        relative_path = self._data.file.relative_to(self._module_root)
        return f'[{self._name}](/{relative_path}#L{self._data.loc})'


@register_model(ParsedHclItem[HclResourceFields])
class ResourceRow(ItemRow[HclResourceFields]):
    """Represents a row in the resource table."""

    # FIXME: Good enough for AWS

    @computed_field
    @property
    def provider(self) -> str:
        """Return the provider of the resource."""
        return self._name.split('_', 1)[0]

    @computed_field
    @property
    def documentation(self) -> str:
        """Return the link to the documentation."""
        provider, name = (self._name.split('.')[0]).split('_', 1)
        return TERRAFORM_URL.format(provider=provider, name=name)


@register_model(ParsedHclItem[HclLocalFields])
class LocalRow(ItemRow[HclLocalFields]):
    """Represents a row in the local variable table."""


@register_model(ParsedHclItem[HclVariableFields])
class VariableRow(ItemRow[HclVariableFields]):
    """Represents a row in the variable table."""

    @computed_field
    @property
    def type(self) -> str:
        """Return the type of the variable."""
        prop = find_prop_in_block(self._data.block, 'type')
        return '<pre>' + prop.replace('\n', '<br/>') + '</pre>'

    @computed_field
    @property
    def description(self) -> str:
        """Return the description of the variable."""
        return format_description(self._data.data.description)

    @computed_field
    @property
    def default(self) -> str:
        """Return the default value of the variable."""
        if self._data.data.required:
            return '**required**'
        prop = find_prop_in_block(self._data.block, 'default')
        return '<pre>' + prop.replace('\n', '<br/>') + '</pre>'

    @computed_field
    @property
    def validation(self) -> str:
        """Return the validation of the variable."""
        return format_validation(self._data.data.validation)


@register_model(ParsedHclItem[HclOutputFields])
class OutputRow(ItemRow[HclOutputFields]):
    """Represents a row in the output table."""

    @computed_field
    @property
    def description(self) -> str:
        """Return the description of the output."""
        return format_description(self._data.data.description)

    @computed_field
    @property
    def value(self) -> str:
        """Return the value of the output."""
        prop = find_prop_in_block(self._data.block, 'value')
        return '<pre>' + prop.replace('\n', '<br/>') + '</pre>'

    @computed_field
    @property
    def precondition(self) -> str:
        """Return the precondition of the output."""
        return format_validation(self._data.data.precondition)

    @computed_field
    @property
    def postcondition(self) -> str:
        """Return the postcondition of the output."""
        if not self._data.data.postcondition:
            return ''
        return ', '.join([v.error_message for v in self._data.data.postcondition])


def get_output_model(input_model_cls):
    """Get the output model associated with the input model."""
    ret = _registry.get(input_model_cls)

    if ret is None:
        _err = f'No output model found for {input_model_cls}'
        raise ValueError(_err)
    return ret
