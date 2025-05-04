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

        self.resource_flat = {}
        self.locals = {}
        self.variable = {}
        self.output = {}

        def _parse_kind(kind: str, allow_duplicates: bool = False):
            data = getattr(self, kind)
            source_data = getattr(self.data, kind)

            for v in source_data:
                k = next(iter(v.root.keys()))
                if k in data and not allow_duplicates:
                    _err = f'Already defined: {kind} {k}'
                    raise ValueError(_err)
                item = v.root[k]
                log.debug(f'Found {kind} {k} as {type(item)}')
                loc, block = v.find(self.hcl)
                data[k] = ParsedHclItem[type(item)](
                    data=item,
                    loc=loc,
                    block=block,
                    file=path,
                )

        _parse_kind('locals')
        _parse_kind('variable')
        _parse_kind('output')

        for v in self.data.resource:
            resource_k = next(iter(v.root.keys()))
            identifier_k = next(iter(v.root[resource_k].root.keys()))
            if settings.config.format.add_resource_identifier:
                name = f'{resource_k}.{identifier_k}'
            else:
                name = resource_k
            resource = HclNamedResource(
                root={
                    name: v.root[resource_k].root[identifier_k],
                }
            )
            object.__setattr__(resource, 'find', v.find)
            self.data.resource_flat.append(resource)

        allow_duplicates = not settings.config.format.add_resource_identifier

        _parse_kind('resource_flat', allow_duplicates=allow_duplicates)
