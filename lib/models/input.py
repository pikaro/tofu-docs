"""Models."""

import logging
import re
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, RootModel, computed_field, field_validator

from lib.common.helper import find_block
from lib.models.dummy import NoDefault

log = logging.getLogger(__name__)


class HclValidation(BaseModel):
    """Represents the validation of a variable in HCL."""

    condition: str
    error_message: str


class HclVariableFields(BaseModel):
    """Represents the fields of a variable in HCL."""

    type: str
    description: str
    default: Any | None | NoDefault = NoDefault()
    validation: list[HclValidation] = []

    @computed_field
    @property
    def required(self) -> bool:
        """Check if the variable is required."""
        return isinstance(self.default, NoDefault)

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class HclOutputFields(BaseModel):
    """Represents the fields of an output in HCL."""

    value: str | None
    description: str
    precondition: list[HclValidation] = []
    postcondition: list[HclValidation] = []


class HclResourceFields(RootModel):
    """Represents the fields of a resource in HCL."""

    root: dict[str, Any]


class HclNamedResource(RootModel):
    """Represents the fields of a resource in HCL."""

    root: dict[str, HclResourceFields]

    @computed_field
    @property
    def name(self) -> str:
        """Return the name of the variable."""
        return next(iter(self.root.keys()))


class HclLocalFields(RootModel):
    """Represents the fields of a local variable in HCL."""

    root: Any


HclDataModel = HclVariableFields | HclOutputFields | HclLocalFields | HclResourceFields

ParsableT = TypeVar('ParsableT', bound=HclDataModel)


class ParsedHclItem(BaseModel, Generic[ParsableT]):
    """Represents the variable fields with the LOC included."""

    data: ParsableT
    loc: int
    block: str
    file: Path


HclListable = HclVariableFields | HclOutputFields | HclLocalFields | HclNamedResource

ListableT = TypeVar('ListableT', bound=HclListable)


class SingleElementRootModel(RootModel[dict[str, ListableT]]):
    """Represents a root model with a single element."""

    root: dict[str, ListableT]
    _start_regex: str
    _end_regex: str = r'^}$'

    @computed_field
    @property
    def name(self) -> str:
        """Return the name of the variable."""
        return next(iter(self.root.keys()))

    @classmethod
    @field_validator('root')
    def validate_root(cls, value: dict[str, ListableT]) -> dict[str, ListableT]:
        """Validate the root of the variable."""
        if len(value) != 1:
            _err = 'There must be exactly one variable defined.'
            raise ValueError(_err)
        return value

    def find(self, file_content: str, start_regex: str | None = None) -> tuple[int, str]:
        """Find the LOC and block of the variable in the file."""
        start_regex = (start_regex or self._start_regex).format(name=self.name)
        pattern = re.search(start_regex, file_content, re.MULTILINE)
        loc = None
        if pattern:
            loc = file_content.count('\n', 0, pattern.start()) + 1
            log.debug(f'Found {start_regex} at LOC {loc}')
        if loc is None:
            _err = f'{start_regex} not found in file'
            raise ValueError(_err)
        block = find_block(file_content, loc, start_regex, end_regex=self._end_regex)
        if block is None:
            _err = f'{start_regex} block not found in file'
            raise ValueError(_err)
        return loc, block


class HclVariable(SingleElementRootModel[HclVariableFields]):
    """Represents a variable in HCL."""

    _start_regex = r'^variable "{name}" {{$'


class HclOutput(SingleElementRootModel[HclOutputFields]):
    """Represents an output in HCL."""

    _start_regex = r'^output "{name}" {{$'

    @computed_field
    @property
    def is_validation(self) -> bool:
        """Check if the output is a validation."""
        return self.name.startswith(('validate_', 'validation_'))


class HclLocal(SingleElementRootModel[HclLocalFields]):
    """Represents a local variable in HCL."""

    _start_regex = r'^locals {{$'


class HclResource(SingleElementRootModel[HclNamedResource]):
    """Represents a resource in HCL."""

    def find(self, file_content: str, start_regex: str | None = None) -> tuple[int, str]:
        """Find the LOC of the variable in the file."""
        identifier = self.root[self.name].name
        start_regex = rf'^resource "{self.name}" "{identifier}" {{{{'
        return super().find(file_content, start_regex=start_regex)


class HclData(BaseModel):
    """Represents a data source in HCL."""

    resource: list[HclResource] = []
    resource_flat: list[HclNamedResource] = []
    locals: list[HclLocal] = []
    variable: list[HclVariable] = []
    output: list[HclOutput] = []
