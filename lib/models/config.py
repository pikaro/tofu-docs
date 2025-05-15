"""Models."""

import logging
import re
from pathlib import Path, PosixPath, WindowsPath
from textwrap import dedent
from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, computed_field, field_validator
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    EnvSettingsSource,
    InitSettingsSource,
    PydanticBaseSettingsSource,
)
from pydantic_settings.sources import ConfigFileSourceMixin
from ruamel.yaml import YAML

from lib.const import RE_SPEC_REPO_WITH_VAR, REPLACE_DEFAULT
from lib.types import InsertPosition, OutputFormat, ReplaceableField, SortOrder

log = logging.getLogger(__name__)


def _path_representer(self, value: Path) -> str:
    """Represent a Path object as a string."""
    return self.represent_scalar('tag:yaml.org,2002:str', str(value.as_posix()), style="'")


yaml = YAML(typ='safe')
yaml.default_flow_style = False
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.representer.add_representer(Path, _path_representer)
yaml.representer.add_representer(PosixPath, _path_representer)
yaml.representer.add_representer(WindowsPath, _path_representer)


class LateYamlConfigSettingsSource(InitSettingsSource, ConfigFileSourceMixin):
    """A source class that loads variables from a yaml file."""

    def __init__(self, default_path: Path):
        """Initialize the YAML config settings source."""
        self.yaml_file = default_path

    def __call__(self) -> dict[str, Any]:
        """Read the YAML file and return its contents."""
        if 'config_file' in self.current_state:
            self.yaml_file = self.current_state['config_file']
        return self._read_files(self.yaml_file)

    def _read_file(self, path: Path) -> dict[str, Any]:
        """Read a YAML file and return its contents as a dictionary."""
        if not path.exists():
            _err = f'Config file {path} does not exist'
            raise FileNotFoundError(_err)
        with path.open(encoding='utf-8') as f:
            return yaml.load(f) or {}

    def __repr__(self) -> str:
        """Return a string representation of the YAML config settings source."""
        return f'{self.__class__.__name__}(yaml_file={self.yaml_file})'


class TargetFileSettings(BaseModel):
    """Settings for the target file."""

    marker: str = 'TOFU_DOCS'
    insert_position: InsertPosition = 'bottom'
    format: OutputFormat = 'markdown'

    heading_level: int = 2
    heading: str = 'API Documentation'
    empty_header: str = dedent("""\
    # {module}

    ## Description

    [tbd]

    ## Usage

    [tbd]

    ## Examples

    [tbd]

    ## Notes

    [tbd]

    """)


class FormatSettings(BaseModel):
    """Settings for filtering the output."""

    collapsible_sections: bool = Field(default=True, description='Collapsible sections')

    collapsible_long_values: bool = Field(default=True, description='Collapsible long values')
    collapsible_long_types: bool = Field(default=True, description='Collapsible long types')
    collapsible_long_defaults: bool = Field(default=True, description='Collapsible long defaults')
    collapsible_long_description: bool = Field(
        default=True, description='Collapsible long description'
    )

    collapsible_long_threshold: int = Field(default=25, description='Collapsible long threshold')

    skip_auto: bool = Field(default=True, description='Skip auto.*.tf files')
    sort_order: SortOrder = Field(default='alpha-asc', description='Sort order')

    validation_remove: bool = Field(default=False, description='Remove validation blocks')
    validation_separate: bool = Field(default=True, description='Separate validation blocks')

    remove_empty_columns: bool = Field(default=True, description='Remove empty columns')

    required_variables_first: bool = Field(default=True, description='Required variables first')
    add_resource_identifier: bool = Field(default=True, description='Add resource identifier')
    add_output_value: bool = Field(default=True, description='Add output value')

    include_resources: bool = Field(default=True, description='Include resources')
    include_locals: bool = Field(default=True, description='Include locals')
    include_variables: bool = Field(default=True, description='Include variables')
    include_outputs: bool = Field(default=True, description='Include outputs')


class ReplaceSetting(BaseModel):
    """Single search-replace for the replace patterns."""

    pattern: str = Field(description='Regex pattern to search for')
    replace: str = Field(description='Replacement string')
    vars: dict[str, str] = Field(
        default_factory=dict, description='Variables to replace in the pattern'
    )
    column: ReplaceableField = Field(description='Column to replace in')


class Settings(BaseSettings):
    """Command-line arguments."""

    dump_config: bool = Field(default=False, description='Dump the configuration')
    dump_overwrite: bool = Field(default=False, description='Overwrite the configuration')
    module_path: Path = Field(default=Path(), description='Path to the module')
    config_file: str = Field(
        default='.tofu-docs.yml',
        description=(
            'Path to the config file. If the path starts with ./, ../ or is absolute, '
            'it will be taken literally; otherwise, it will be resolved relative to the module path'
        ),
    )

    debug: bool = Field(default=False, description='Enable debug mode')
    changed_exit_code: int = Field(
        default=0, description=('Exit code to return if the output file has changed. ')
    )

    target: str = Field(
        default='README.md',
        description=(
            'Path to the target file. If the path starts with ./, ../ or is absolute, '
            'it will be taken literally; otherwise, it will be resolved relative to the module path'
        ),
    )

    target_config: TargetFileSettings = TargetFileSettings()
    format: FormatSettings = FormatSettings()
    replace: list[ReplaceSetting] = [
        ReplaceSetting(
            pattern=rf'repo {RE_SPEC_REPO_WITH_VAR}',
            replace=REPLACE_DEFAULT,
            vars={'namespace': 'globaldatanet/'},
            column='description',
        ),
        ReplaceSetting(
            pattern=rf'module {RE_SPEC_REPO_WITH_VAR}',
            replace=REPLACE_DEFAULT,
            vars={'namespace': 'globaldatanet/landing-zone-'},
            column='description',
        ),
        ReplaceSetting(
            pattern=rf'any\s+#\s+passthrough to repo {RE_SPEC_REPO_WITH_VAR}',
            replace=f'See {REPLACE_DEFAULT}',
            vars={'namespace': 'globaldatanet/'},
            column='type',
        ),
        ReplaceSetting(
            pattern=rf'any\s+#\s+passthrough to module {RE_SPEC_REPO_WITH_VAR}',
            replace=f'See {REPLACE_DEFAULT}',
            vars={'namespace': 'globaldatanet/landing-zone-'},
            column='type',
        ),
    ]

    @computed_field
    @property
    def replace_formatted(self) -> list[ReplaceSetting]:
        """Return the replacements formatted for the output."""
        return [
            ReplaceSetting(
                pattern=replace.pattern.format(**replace.vars),
                replace=replace.replace.format(**replace.vars),
                column=replace.column,
            )
            for replace in self.replace
        ]

    @field_validator('config_file')
    @classmethod
    def validate_config_file(cls, value: str, info: ValidationInfo) -> str:
        """Apply the command line arguments, parsing a config file and retrieving the settings."""
        path = Path(value)
        if path.is_dir():
            _err = f'Config file {value} is a directory'
            raise ValueError(_err)
        if not path.parent.exists():
            _err = f'Config file {value} parent directory does not exist'
            raise ValueError(_err)
        default_path = cls.__pydantic_fields__['config_file'].default
        if not path.is_absolute() and not re.match(r'^\.\.?/', value):
            if value != default_path:
                log.warning(f'Config file {value} is not absolute - using module path')
            value = (info.data['module_path'] / value).resolve().as_posix()
        return value

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: type[BaseSettings], *_args, **_kwargs
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Workaround for lack of ability to specify path to the config file."""
        _ = (_args, _kwargs)
        default_path = settings_cls.__pydantic_fields__['config_file'].default
        return (
            CliSettingsSource(
                settings_cls,
                cli_parse_args=True,
                cli_kebab_case=True,
                cli_implicit_flags=True,
            ),
            EnvSettingsSource(
                settings_cls,
                env_prefix='TOFU_DOCS_',
            ),
            LateYamlConfigSettingsSource(
                default_path,
            ),
        )

    def dump(self):
        """Dump the settings to a config file."""
        config_file = Path(self.config_file)

        if config_file.exists() and self.dump_config and not self.dump_overwrite:
            _err = f'Config file {self.config_file} already exists'
            raise ValueError(_err)

        if self.dump_config:
            log.info(f'Dumping settings to {self.config_file}')
            with config_file.open('w', encoding='utf-8') as f:
                config = self.model_dump(round_trip=True)
                yaml.dump(
                    {k: v for k, v in config.items() if k not in self.Config.cli_only_args}, f
                )

    class Config:
        """Settings configuration."""

        env_nested_delimiter = '__'
        env_ignore_empty = True
        cli_only_args = {'dump_config', 'dump_overwrite', 'config_file', 'module_path'}  # noqa: RUF012 # mutable class var


settings = Settings()
root_log = logging.getLogger()
root_log.setLevel(logging.DEBUG if settings.debug else logging.INFO)
