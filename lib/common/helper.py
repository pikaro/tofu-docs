"""Common functions."""

import logging
import re

from lib.settings import settings

log = logging.getLogger(__name__)


def find_block(text: str, loc: int, start_regex: str, end_regex: str = r'^}$') -> str:
    """Get a block of text from the LOC, starting with start_regex and ending with end_regex."""
    lines = text.splitlines()
    idx = loc - 1
    if not lines or not lines[idx:]:
        _err = f'Invalid LOC: {loc}, found {lines}'
        raise ValueError(_err)
    if not re.match(start_regex, lines[idx]):
        _err = f'Invalid start regex: {start_regex}, found {lines[idx]} on LOC {loc}'
        raise ValueError(_err)
    block = []
    in_block = True
    line = ''
    for line in lines[idx:]:
        block.append(line)
        if re.match(end_regex, line):
            in_block = False
            break
    if in_block:
        _err = f'Invalid end regex: {end_regex}, found {line}'
        raise ValueError(_err)
    return '\n'.join(block)


BRACKETS = {
    '}': '{',
    ']': '[',
    ')': '(',
}

RE_HEREDOC = re.compile(r'<<-?(\w+)')


# Terrible but it works for now.
# The HCL parser only returns collapsed strings, so we need to retrieve them from the original
# file.
def find_prop_in_block(text: str, prop: str) -> str:  # noqa: C901 PLR0912 # Too many branches
    """Find a property in an HCL block."""
    matches = list(re.finditer(rf'^\s*{prop}\s*=', text, re.MULTILINE))
    if len(matches) > 1:
        # Identify the match with the least number of leading spaces.
        # Catches cases where there's a nested object with e.g. a `default` propert.
        log.warning(f'Found {len(matches)} matches for {prop} in block')
        matches.sort(key=lambda m: len(m.group(0)) - len(m.group(0).lstrip()))
    idx = matches[0].start()
    bracket_stack = []
    line_ended = False
    in_quoted = False
    in_heredoc = False
    is_escaped = False
    heredoc_name = None
    ret = ''

    def _in_text():
        return in_quoted or in_heredoc

    while idx < len(text):
        c = text[idx]
        ret += c
        # log.debug(
        #    f'c: {c}, idx: {idx}, line_ended: {line_ended}, '
        #    f'bracket_stack: {bracket_stack}, ret: {ret}, '
        #    f'in_quoted: {in_quoted}, in_heredoc: {in_heredoc}, '
        #    f'heredoc_name: {heredoc_name}'
        # )
        if c == '"' and not in_heredoc and not is_escaped:
            in_quoted = not in_quoted
        elif c == '<' and not _in_text() and (match := re.match(RE_HEREDOC, text[idx:])):
            in_heredoc = True
            heredoc_name = match.group(1)
            idx += len(match.group(0))
            ret += f'<<-{heredoc_name}'
        elif (
            in_heredoc
            and not in_quoted
            and heredoc_name
            and text.startswith(heredoc_name + '\n', idx)
            and text[idx - 1] == '\n'
        ):
            in_heredoc = False
            idx += len(heredoc_name)
            if text[idx] == '\n':
                idx += 1
            if line_ended:
                break
        elif c in '{[(' and not in_quoted and not in_heredoc:
            bracket_stack.append(c)
        elif c in '}])' and not in_quoted and BRACKETS.get(c) == bracket_stack[-1]:
            bracket_stack.pop()
            if line_ended and not bracket_stack:
                break
        elif c in '}])' and not in_quoted:
            _err = f'Unmatched brackets in {prop} block'
            raise ValueError(_err)
        elif c == '\n':
            line_ended = True
            if not _in_text() and not bracket_stack:
                break
        idx += 1
        is_escaped = c == '\\' and not is_escaped
    if bracket_stack:
        _err = f'Unmatched brackets in {prop} block'
        raise ValueError(_err)
    return re.sub(rf'^\s*{prop}\s*=\s*', '', ret, count=1).strip()


def marker(kind: str) -> str:
    """Return the marker for the given kind."""
    return f'<!-- {settings.config.target_config.marker} {kind} -->'


def if_index(lst: list[str], item: str) -> int:
    """Return the index of the item in the list or -1 if not found."""
    try:
        return lst.index(item)
    except ValueError:
        return -1
