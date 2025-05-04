"""Models."""

import logging
import re
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import (
    BaseModel,
    RootModel,
    computed_field,
    model_validator,
)

from lib.common.helper import find_blocks, indent
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


class HclRootModel(RootModel[dict[str, ListableT]]):
    """Represents a root model with a single element."""

    root: dict[str, ListableT]
    _start_regex: str
    _end_regex: str = r'^}$'


class SingleElementRootModel(HclRootModel[ListableT]):
    """Represents a root model with a single element."""

    @computed_field
    @property
    def name(self) -> str:
        """Return the name of the variable."""
        return next(iter(self.root.keys()))

    @model_validator(mode='after')
    def validate_root(self):
        """Validate the root of the element."""
        if len(self.root) != 1:
            _err = 'There must be exactly one element defined.'
            raise ValueError(_err)
        return self

    def find(self, file_content: str, start_regex: str | None = None) -> list[tuple[int, str]]:
        """Find the LOC and block of the variable in the file."""
        start_regex = (start_regex or self._start_regex).format(name=self.name)
        patterns = list(re.finditer(start_regex, file_content, re.MULTILINE))
        locs: list[int] = []
        if patterns:
            for pattern in patterns:
                loc = file_content.count('\n', 0, pattern.start()) + 1
                log.debug(f'Found {start_regex} at LOC {loc}')
                locs.append(loc)
        if not locs:
            _err = f'{start_regex} not found in file'
            raise ValueError(_err)
        blocks = find_blocks(file_content, locs, start_regex, end_regex=self._end_regex)
        return [(loc, block) for loc, block in zip(locs, blocks, strict=False)]


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


class HclLocalBlock(HclRootModel[HclLocalFields]):
    """Represents a local block in HCL.

    As parsed by hcl2, the individual variables are properties on a local block, not separate items.
    This breaks the SingleElementRootModel, e.g. for self.name.
    """


class HclLocal(SingleElementRootModel[HclLocalFields]):
    """Represents a single local variable in HCL."""

    _start_regex = r'^locals {{$'

    def find(self, file_content: str, start_regex: str | None = None) -> list[tuple[int, str]]:
        """Find the LOC of the variable in the file."""
        block_matches = super().find(file_content, start_regex=start_regex)
        loc_matches: list[tuple[int, str, int]] = []
        for loc, block in block_matches:
            matches = list(re.finditer(rf'^\s*{self.name}\s*=', block, re.MULTILINE))

            if not matches:
                log.debug(f'No matches for {self.name} in block')
                continue

            if len(matches) > 1:
                log.warning(f'Found {len(matches)} matches for {self.name} in block')
                matches.sort(key=lambda m: indent(m.group(0)))
            prev = block[: matches[0].start()]
            prev_lines = len(prev.split('\n')) - 1
            loc_matches.append((loc + prev_lines, block, indent(matches[0].group(0))))

        if not loc_matches:
            _err = f'{self.name} not found in file'
            raise ValueError(_err)
        loc_matches.sort(key=lambda m: m[2])
        return [(loc_matches[0][0], loc_matches[0][1])]


class HclResource(SingleElementRootModel[HclNamedResource]):
    """Represents a resource in HCL."""

    def find(self, file_content: str, start_regex: str | None = None) -> list[tuple[int, str]]:
        """Find the LOC of the variable in the file."""
        identifier = self.root[self.name].name
        start_regex = rf'^resource "{self.name}" "{identifier}" {{{{'
        return super().find(file_content, start_regex=start_regex)


class HclData(BaseModel):
    """Represents a data source in HCL."""

    resource: list[HclResource] = []
    locals: list[HclLocalBlock] = []
    variable: list[HclVariable] = []
    output: list[HclOutput] = []


class ProcessedData(BaseModel):
    """Represents the processed data from HCL."""

    resource: list[HclNamedResource] = []
    locals: list[HclLocal] = []
    variable: list[HclVariable] = []
    output: list[HclOutput] = []
    validation: list[HclOutput] = []


class ParsedData(BaseModel):
    """Represents the parsed data from HCL."""

    resource: dict[str, ParsedHclItem[HclResourceFields]] = {}
    locals: dict[str, ParsedHclItem[HclLocalFields]] = {}
    variable: dict[str, ParsedHclItem[HclVariableFields]] = {}
    output: dict[str, ParsedHclItem[HclOutputFields]] = {}
    validation: dict[str, ParsedHclItem[HclOutputFields]] = {}
