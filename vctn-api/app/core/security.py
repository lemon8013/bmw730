"""Security boundary (Phase 0 reserved).

Authentication, session, MFA, token issuing and password handling are NOT
implemented in Phase 0. They stay blocked until the project owner freezes:

- MFA V1 provider and full flow
- access / refresh token TTL
- Redis key and TTL specification
- secret manager

Implementations must never log credentials, tokens or secrets.
"""
