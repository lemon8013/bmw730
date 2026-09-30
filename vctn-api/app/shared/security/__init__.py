"""Security shared infrastructure.

Passwords, tokens, secret masking and MFA abstraction live here. Nothing in
this package may ever write a password, an MFA secret, a raw token or raw user
input to a log record.
"""
