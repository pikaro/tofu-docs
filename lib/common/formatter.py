"""Common functions."""

import re

from lib.common.helper import field_replace
from lib.models.input import HclValidation
from lib.types import ValidationField

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
    ret = field_replace('description', ret)
    return ret  # noqa: RET504  # Unnecessary assign - easier to expand


def format_validation(field: ValidationField, validation: list[HclValidation]) -> str:
    """Format the validation errors."""
    if not validation:
        return ''
    validation_replaced = [field_replace(field, v.error_message) for v in validation]
    return '<ul>' + ''.join(['<li>' + v + '</li>' for v in validation_replaced]) + '</ul>'
