"""Models."""

import logging
import os
from pathlib import Path
from textwrap import dedent

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from lib.const import SETTINGS_FILE
from lib.types import InsertPosition, OutputFormat, SortOrder

log = logging.getLogger(__name__)


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

    tbd

    ## Examples

    tbd

    ## Notes

    tbd

    """)


class FormatSettings(BaseModel):
    """Settings for filtering the output."""

    collapsible_sections: bool = True

    collapsible_long_values: bool = True
    collapsible_long_types: bool = True
    collapsible_long_defaults: bool = True
    collapsible_long_description: bool = True

    collapsible_long_threshold: int = 25

    skip_auto: bool = True
    sort_order: SortOrder = 'alpha-asc'

    remove_validation: bool = True
    remove_empty_columns: bool = True

    required_variables_first: bool = True
    add_resource_identifier: bool = True
    add_output_value: bool = False

    include_resources: bool = True
    include_locals: bool = True
    include_variables: bool = True
    include_outputs: bool = True


class Settings(BaseSettings):
    """Command-line arguments."""

    debug: bool = False

    target: Path = Path('README.md')
    target_config: TargetFileSettings = TargetFileSettings()
    format: FormatSettings = FormatSettings()

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: type[BaseSettings], *_, **__
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Workaround for lack of ability to specify path to the config file."""
        settings_path = Path(os.getenv('TOFU_DOCS_CONFIG', f'./{SETTINGS_FILE}'))
        return (
            EnvSettingsSource(
                settings_cls,
                env_prefix='TOFU_DOCS_',
            ),
            YamlConfigSettingsSource(settings_cls, settings_path),
        )

    class Config:
        """Settings configuration."""

        env_nested_delimiter = '__'


class CliArgs(BaseModel):
    """Command-line arguments."""

    module_path: Path = Field(default=Path(), description='Path to the module')
    dump_config: bool = Field(default=False, description='Dump the configuration')
    dump_overwrite: bool = Field(default=False, description='Overwrite the configuration')
    config_file: Path | None = Field(default=None, description='Path to the config file')

    # These override the values from the config file if set, i.e. not None
    target: Path | None = Field(default=None, description='Path to the target file')
    debug: bool | None = Field(default=None, description='Enable debug mode')
