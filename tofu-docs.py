#!/usr/bin/env python3

"""Generate Markdown documentation from OpenTofu source code."""

import logging
import sys

import colorlog

from lib.writer import NotAFileException

if __name__ == '__main__':
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            (
                '%(white)s%(asctime)s - %(name)-16s%(reset)s - '
                '%(log_color)s%(levelname)-8s %(reset)s - %(message)s'
            ),
            datefmt='%H:%M:%S',
            style='%',
        )
    )

    root_log = logging.getLogger()
    root_log.addHandler(handler)

    from lib.hcl_module import HclModule
    from lib.models.config import settings
    from lib.writer import Writer

    settings.dump()

    log = logging.getLogger(__name__)

    log.info(f'Generating documentation for {settings.module_path}')
    log.debug('Debug mode is enabled')

    module = HclModule()

    log.info('Generating documentation')

    output = module.format()

    try:
        writer = Writer(output)
    except NotAFileException:
        sys.exit(settings.unchanged_exit_code)

    writer.write()

    if not writer.changed:
        log.info('Documentation was not changed')
        sys.exit(settings.unchanged_exit_code)

    if settings.changed_git_add:
        log.info('Adding changes to git')
        writer.git_add()

    sys.exit(settings.changed_exit_code)
