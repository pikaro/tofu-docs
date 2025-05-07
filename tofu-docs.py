#!/usr/bin/env python3

"""Generate Markdown documentation from OpenTofu source code."""

import logging
import sys
from difflib import unified_diff

import colorlog

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

    writer = Writer()
    result = writer.write(output)

    if result.changed and result.original_content:
        log.warning('Documentation was changed')

        if settings.debug:
            diff = unified_diff(
                result.original_content.splitlines(),
                result.content.splitlines(),
                lineterm='',
            )
            log.debug(f'Diff for {settings.module_path / settings.target}:')
            print('\n    '.join(diff))
    elif not result.original_content:
        log.warning('File was created')

    if result.changed:
        sys.exit(settings.changed_exit_code)

    log.info('Documentation was not changed')
