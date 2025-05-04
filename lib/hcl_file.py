"""Represents a HCL file."""

import logging
from pathlib import Path

import hcl2

from lib.models.input import (
    HclData,
    HclLocalFields,
    HclNamedResource,
    HclOutputFields,
    HclResourceFields,
    HclVariableFields,
    ParsedHclItem,
)
from lib.settings import settings

log = logging.getLogger(__name__)


class HclFile:
    """Represents an HCL file."""

    hcl: str
    data: HclData

    resource_flat: dict[str, ParsedHclItem[HclResourceFields]]
    locals: dict[str, ParsedHclItem[HclLocalFields]]
    variable: dict[str, ParsedHclItem[HclVariableFields]]
    output: dict[str, ParsedHclItem[HclOutputFields]]

    def __init__(self, path: Path):
        """Initialize an HCL file."""
        log.info(f'Parsing {path}')

        with path.open('r', encoding='utf-8') as f:
            self.hcl = f.read()

        self.data = HclData.model_validate(hcl2.loads(self.hcl))  # pyright: ignore[reportPrivateImportUsage]

        if settings.config.format.remove_validation:
            validations = [v for v in self.data.output if v.is_validation]
            if validations:
                validation_names = [v.name for v in validations]
                self.data.output = list(filter(lambda x: x not in validations, self.data.output))
                log.warning(f'Removed {len(validations)} validations: {validation_names}')

        self.resource_flat = {}
        self.locals = {}
        self.variable = {}
        self.output = {}

        def _parse_kind(kind: str, allow_duplicates: bool = False):
            data = getattr(self, kind)
            source_data = getattr(self.data, kind)

            for v in source_data:
                if v.name in data and not allow_duplicates:
                    _err = f'Already defined: {kind} {v.name}'
                    raise ValueError(_err)
                item = v.root[v.name]
                log.debug(f'Found {kind} {v.name} as {type(item)}')
                loc, block = v.find(self.hcl)
                data[v.name] = ParsedHclItem[type(item)](
                    data=item,
                    loc=loc,
                    block=block,
                    file=path,
                )

        _parse_kind('locals')
        _parse_kind('variable')
        _parse_kind('output')

        for v in self.data.resource:
            identifier = v.root[v.name].name
            if settings.config.format.add_resource_identifier:
                name = f'{v.name}.{identifier}'
            else:
                name = v.name
            resource = HclNamedResource(
                root={
                    name: v.root[v.name].root[identifier],
                }
            )
            object.__setattr__(resource, 'find', v.find)
            self.data.resource_flat.append(resource)

        allow_duplicates = not settings.config.format.add_resource_identifier

        _parse_kind('resource_flat', allow_duplicates=allow_duplicates)
