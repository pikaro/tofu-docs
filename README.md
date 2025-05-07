# tofu-docs

## Description

`tofu-docs` is a (very limited) `terraform-docs` replacement that generates
documentation for OpenTofu modules in Markdown format. This is a stopgap project
while `terraform-docs` still doesn't support all OpenTofu features.

The output format is similar to `terraform-docs`, but not a drop-in replacement.

The goal of `tofu-docs` is only to generate README files for OpenTofu modules,
and it lacks many other features that `terraform-docs` has.

## Installation

Either run it locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
poetry install
tofu-docs --module_path <path>
```

Or via Docker:

```bash
docker run -v .:/module 70696b61726f/tofu-docs:latest
```

Or via `pre-commit`:

```yaml
- repo: https://github.com/pikaro/tofu-docs
  rev: v0.3.0
  hooks:
    - id: tofu-docs
```

For CLI arguments, see `tofu-docs --help`.

## Configuration

Most settings are configured with `.tofu-docs.yml` in the module root. You can
dump the default configuration to the file with `--dump_config`.

The default configuration is:

```yaml
debug: false

# The exit code to return if changes were made to the documentation
changed_exit_code: 0

# Target file to write the documentation to
# README.md would be relative to the module path
# ./README.md would be in the current working directory
target: 'README.md'

target_config:
  # Start / end marker comment in the target file
  marker: TOFU_DOCS
  # Valid values: bottom.
  insert_position: bottom
  # Valid values: markdown.
  format: markdown
  # Heading depth to use for the documentation
  heading_level: 2
  # Heading to use for the documentation (i.e. with depth 2, '## API Documentation')
  heading: API Documentation
  # Template to use if the target file is absent
  empty_header: "# {module}\n\n## Description\n\n[tbd]\n\n## Usage\n\ntbd\n\n## Examples\n
    \ntbd\n\n## Notes\n\ntbd\n\n"

format:
  # Make sections (resources / variables / etc.) collapsible
  collapsible_sections: true
  # Inside the tables, for each column, make the content collapsible
  collapsible_long_values: true
  collapsible_long_types: true
  collapsible_long_defaults: true
  # For the documentation, first line is always uncollapsed (use multiline heredocs)
  collapsible_long_description: true
  # Threshold for the number of characters to consider a value long
  collapsible_long_threshold: 25
  # Skip auto.*.tf files
  skip_auto: true
  # Valid values: alpha-asc.
  sort_order: alpha-asc
  # Remove outputs starting with `validation_` and `validate_`
  validation_remove: false
  # Put validations in a separate section
  validation_separate: true
  # Remove empty columns from the tables
  remove_empty_columns: true
  # Make a separate section for required / optional variables
  required_variables_first: true
  # Include resources with `<resource>.<identifier>` format (for linking to code)
  add_resource_identifier: true
  # Include the value of outputs in the documentation
  add_output_value: false
  # Include resources in the documentation
  include_resources: true
  # Include locals in the documentation
  include_locals: true
  # Include variables in the documentation
  include_variables: true
  # Include outputs in the documentation
  include_outputs: true

# A list of patterns to search-replace per column, using Python regex.
replace:
    # The pattern to search for
  - pattern: repo `([^`.]+)(\.([^`]+))?`
    # the replacement string, with curly braces for references to `vars`
    replace: '[\1](https://github.com/{namespace}\1/README.md#user-content-\3)'
    # A dictionary of variables to replace in the replacement string
    vars:
      namespace: globaldatanet/
    # The column to search in
    column: description
  - pattern: module `([^`.]+)(\.([^`]+))?`
    replace: '[\1](https://github.com/{namespace}\1/README.md#user-content-\3)'
    vars:
      namespace: globaldatanet/landing-zone-
    column: description
  - pattern: ^any\s+#\s+passthrough to repo `([^`.]+)(\.([^`]+))?`$
    replace: See [\1](https://github.com/{namespace}\1/README.md#user-content-\3)
    vars:
      namespace: globaldatanet/
    column: type
  - pattern: ^any\s+#\s+passthrough to module `([^`.]+)(\.([^`]+))?`$
    replace: See [\1](https://github.com/{namespace}\1/README.md#user-content-\3)
    vars:
      namespace: globaldatanet/landing-zone-
    column: type
```

## Caveat

This is very WIP and written for my own and my team's needs and coding style.
The `hcl2` module for Python isn't very full-featured, so there's a lot of
fragile text parsing with regex. YMMV, but feel free to report any bugs or
suggestions.
