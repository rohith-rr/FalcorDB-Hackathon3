"""Canonical identity helpers.

IDs are namespaced by tenant, provider and native scope (graph_schema.md):
`demo:jira:PAY:PAY-API`, `demo:github:123:branch:feature/backend-service`,
`demo:git:123:commit:<full-sha>`. Contracts reject unscoped IDs.
"""

from __future__ import annotations

import re
from typing import Optional

# Tenant, provider and native scope are all required; further details are optional.
_SCOPED_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]*(?::[A-Za-z0-9][A-Za-z0-9._/-]*){2,}")

#: Git full commit SHA.
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class UnscopedIdError(ValueError):
    """Raised when an ID does not carry tenant/provider/scope namespaces."""


def is_scoped_id(value: object) -> bool:
    return isinstance(value, str) and bool(_SCOPED_ID_RE.fullmatch(value))


def parse_scoped_id(value: str, *, field: str = "id") -> str:
    if not is_scoped_id(value):
        raise UnscopedIdError(
            f"{field} '{value}' is not a scoped application ID "
            "(expected 'tenant:provider:scope[:detail]')"
        )
    return value


def task_key_to_id(tenant: str, provider: str, project: str, key: str) -> str:
    return f"{tenant}:{provider}:{project}:{key}"


def tenant_of(value: str) -> Optional[str]:
    if is_scoped_id(value):
        return value.split(":", 1)[0]
    return None
