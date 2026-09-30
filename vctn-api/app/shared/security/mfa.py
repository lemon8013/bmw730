"""MFA abstraction.

The Spec freezes "MFA must be extensible" but does **not** freeze a provider.
No provider is therefore selected here: this module only defines the contract a
provider must satisfy plus a registry that is empty until the project owner
freezes one.

Because the registry starts empty, authentication is never blocked: an account
without a usable provider logs in with its password alone.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MfaProvider(Protocol):
    """Contract every MFA provider must implement."""

    factor_type: str

    async def start_enrollment(self, *, user_id: int, username: str) -> tuple[str, str]:
        """Return ``(challenge_reference, secret_ciphertext)`` for enrollment."""
        ...

    async def complete_enrollment(self, *, secret_ciphertext: str, code: str) -> bool:
        """Return whether the enrollment proof is valid."""
        ...

    async def verify(self, *, secret_ciphertext: str, code: str) -> bool:
        """Return whether a login proof is valid."""
        ...


class MfaProviderRegistry:
    """Holds the provider registered for each factor type."""

    def __init__(self) -> None:
        self._providers: dict[str, MfaProvider] = {}

    def register(self, provider: MfaProvider) -> None:
        self._providers[provider.factor_type] = provider

    def get(self, factor_type: str) -> MfaProvider | None:
        return self._providers.get(factor_type)

    def factor_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def is_empty(self) -> bool:
        return not self._providers


_REGISTRY = MfaProviderRegistry()


def get_registry() -> MfaProviderRegistry:
    """Return the process wide MFA provider registry."""
    return _REGISTRY
