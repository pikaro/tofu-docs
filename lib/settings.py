"""Settings module for the application."""

import logging
import os
from pathlib import Path, PosixPath, WindowsPath

from ruamel.yaml import YAML
from tap import tapify

from lib.const import SETTINGS_FILE
from lib.models.config import CliArgs, Settings

log = logging.getLogger(__name__)


class SingletonMeta(type):
    """Singleton metaclass."""

    _instances = {}  # noqa: RUF012 # Not mutable

    def __call__(cls, *args, **kwargs):
        """Return the singleton instance."""
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


def path_representer(self, value: Path) -> str:
    """Represent a Path object as a string."""
    return self.represent_scalar('tag:yaml.org,2002:str', str(value.as_posix()), style="'")


class SettingsSingleton(metaclass=SingletonMeta):
    """Settings for the application."""

    config: Settings
    args: CliArgs

    config_file: Path

    def __init__(self):
        """Initialize settings."""
        self.args = tapify(CliArgs)

        if not self.args.config_file:
            self.config_file = self.args.module_path / SETTINGS_FILE

        self._validate()
        self._dump()

        if self.config_file.exists():
            log.info(f'Loading settings from {self.config_file}')
            os.environ['TOFU_DOCS_CONFIG'] = str(self.config_file)
        else:
            log.info(f'Settings file {self.config_file} does not exist, using defaults')

        self.config = Settings()

        self._override()

    def _validate(self):
        if self.config_file.is_dir():
            _err = f'Config file {self.config_file} is a directory'
            raise ValueError(_err)

    def _dump(self):
        if self.config_file.exists() and self.args.dump_config and not self.args.dump_overwrite:
            _err = f'Config file {self.config_file} already exists'
            raise ValueError(_err)

        if self.args.dump_config:
            log.info(f'Dumping settings to {self.config_file}')
            yaml = YAML()
            yaml.default_flow_style = False
            yaml.indent(mapping=2, sequence=4, offset=2)
            yaml.representer.add_representer(Path, path_representer)
            yaml.representer.add_representer(PosixPath, path_representer)
            yaml.representer.add_representer(WindowsPath, path_representer)
            self.config = Settings()
            with self.config_file.open('w', encoding='utf-8') as f:
                yaml.dump(self.config.model_dump(round_trip=True), f)

    def _override(self):
        for k, v in self.args.model_dump().items():
            if k in self.config.model_dump(round_trip=True) and v is not None:
                setattr(self.config, k, v)


settings = SettingsSingleton()
