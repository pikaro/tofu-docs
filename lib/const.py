"""Constants."""

TERRAFORM_URL = (
    '[{name}]'
    '(https://registry.terraform.io/providers/hashicorp/{provider}/latest/docs/resources/{name})'
)

RE_SPEC_REPO_WITH_VAR = r'`([^`.]+)(\.([^`]+))?`'
REPLACE_DEFAULT = r'[\1](https://github.com/{namespace}\1/README.md#user-content-\3)'
