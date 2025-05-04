"""Represents a HCL file."""

import logging
from pathlib import Path

import hcl2

from lib.models.input import (
    HclData,
    HclLocal,
    HclNamedResource,
    ParsedData,
    ParsedHclItem,
    ProcessedData,
)
from lib.settings import settings

log = logging.getLogger(__name__)


class HclFile:
    """Represents an HCL file."""

    _hcl: str
    _data: HclData
    _data_processed: ProcessedData
    _data_parsed: ParsedData

    def __init__(self, path: Path):
        """Initialize an HCL file."""
        log.info(f'Parsing {path}')

        with path.open('r', encoding='utf-8') as f:
            self._hcl = f.read()

        self._data = HclData.model_validate(hcl2.loads(self._hcl))  # pyright: ignore[reportPrivateImportUsage]

        self._data_processed = ProcessedData()
        self._data_parsed = ParsedData()

        self._process_locals()
        self._process_validation()
        self._process_resource()
        self._process_variable()
        self._process_output()

        def _parse_kind(kind: str, allow_duplicates: bool = False):
            data = getattr(self._data_parsed, kind)
            source_data = getattr(self._data_processed, kind)

            for v in source_data:
                if v.name in data and not allow_duplicates:
                    _err = f'Already defined: {kind} {v.name}'
                    raise ValueError(_err)
                item = v.root[v.name]
                log.debug(f'Found {kind} {v.name} as {type(item)}')
                match = v.find(self._hcl)
                if len(match) != 1:
                    _err = f'Found {len(match)} matches for {v.name}'
                    raise ValueError(_err)
                loc, block = match[0]
                data[v.name] = ParsedHclItem[type(item)](
                    data=item,
                    loc=loc,
                    block=block,
                    file=path,
                )

        _parse_kind('locals')
        _parse_kind('variable')
        _parse_kind('output')
        _parse_kind('validation')

        allow_duplicates = not settings.config.format.add_resource_identifier

        _parse_kind('resource', allow_duplicates=allow_duplicates)

    def _process_locals(self):
        """Process the locals in the file."""
        single_locals: list[HclLocal] = []
        for local_block in self._data.locals:
            for local_name, local in local_block.root.items():
                single_locals.append(
                    HclLocal(  # pyright: ignore[reportCallIssue] # wants the _start_regex that's already on the class?
                        root={local_name: local},
                    )
                )
        self._data_processed.locals = single_locals

    def _process_validation(self):
        """Process the validations in the file."""
        if settings.config.format.validation_remove or settings.config.format.validation_separate:
            validations = [v for v in self._data.output if v.is_validation]
            if validations:
                validation_names = [v.name for v in validations]
                self._data.output = list(filter(lambda x: x not in validations, self._data.output))
                log.warning(f'Removed {len(validations)} validations: {validation_names}')
            if settings.config.format.validation_separate:
                self._data_processed.validation = validations

    def _process_resource(self):
        """Process the resources in the file."""
        for v in self._data.resource:
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
            self._data_processed.resource.append(resource)

    def _process_variable(self):
        """Process the variables in the file."""
        self._data_processed.variable = self._data.variable

    def _process_output(self):
        """Process the outputs in the file."""
        self._data_processed.output = self._data.output

    def get_parsed_data(self) -> ParsedData:
        """Return the parsed data."""
        return self._data_parsed
