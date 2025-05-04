#!/usr/bin/env python3

"""Generate Markdown documentation from OpenTofu source code."""

import logging

import colorlog

from lib.writer import Writer

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
    root_log.setLevel(logging.INFO)

    log = logging.getLogger(__name__)

    from lib.hcl_module import HclModule
    from lib.settings import settings

    root_log.setLevel(logging.DEBUG if settings.config.debug else logging.INFO)

    log.info(f'Generating documentation for {settings.args.module_path}')
    log.debug('Debug mode is enabled')

    module = HclModule()

    log.info('Generating documentation')

    output = module.format()

    writer = Writer()
    writer.write(output)
