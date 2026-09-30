"""Unit tests for the trace context."""

from __future__ import annotations

from app.shared.tracing.context import (
    get_request_id,
    get_trace_id,
    reset_trace_context,
    set_trace_context,
)


def test_context_is_empty_by_default() -> None:
    assert get_trace_id() is None
    assert get_request_id() is None


def test_context_roundtrip() -> None:
    tokens = set_trace_context("trace-1", "request-1")
    try:
        assert get_trace_id() == "trace-1"
        assert get_request_id() == "request-1"
    finally:
        reset_trace_context(tokens)

    assert get_trace_id() is None
    assert get_request_id() is None


def test_nested_context_restores_previous_values() -> None:
    outer = set_trace_context("trace-outer", "request-outer")
    try:
        inner = set_trace_context("trace-inner", "request-inner")
        assert get_trace_id() == "trace-inner"
        reset_trace_context(inner)
        assert get_trace_id() == "trace-outer"
    finally:
        reset_trace_context(outer)
