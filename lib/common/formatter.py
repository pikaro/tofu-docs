"""Common functions."""

import re

from lib.models.input import HclValidation

RE_UL = re.compile(r'<li>(.+)</li>')
RE_LI = re.compile('^- (.+)$')
RE_BR = re.compile(r'</li><br/>')


def format_description(desc: str) -> str:
    """Format the description."""
    if not desc:
        return ''
    ret = desc.strip()
    ret = [RE_LI.sub(r'<li>\1</li>', v.strip()) for v in desc.splitlines()]
    ret = '<br/>'.join(ret)
    ret = RE_UL.sub(r'<ul><li>\1</li></ul>', ret)
    ret = RE_BR.sub('</li>', ret)
    return ret  # noqa: RET504 # Unnecessary assign - easier to expand


def format_validation(validation: list[HclValidation]) -> str:
    """Format the validation errors."""
    if not validation:
        return ''
    return '<ul>' + ''.join(['<li>' + v.error_message + '</li>' for v in validation]) + '</ul>'
