"""Snowflake identifier generator.

Every VCTN identifier is a signed 64 bit integer produced by this generator.
The Spec freezes "BIGINT + Snowflake" but leaves the bit layout (DD-14)
unfrozen, therefore the layout is **configuration**, not code: the epoch, the
node id and the two bit widths are read from :class:`app.core.config.Settings`.

Layout used by the shipped defaults::

    sign (1) | timestamp (41) | node (10) | sequence (12)

Only 22 bits are split between node and sequence so that 41 bits stay available
for the timestamp regardless of how the operator divides them.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.core.config import Settings, get_settings

_SIGN_BITS: int = 1
_TOTAL_BITS: int = 64


@dataclass(frozen=True, slots=True)
class SnowflakeLayout:
    """Resolved snowflake bit layout."""

    epoch_ms: int
    node_id: int
    node_bits: int
    sequence_bits: int

    @property
    def timestamp_bits(self) -> int:
        return _TOTAL_BITS - _SIGN_BITS - self.node_bits - self.sequence_bits

    @property
    def max_sequence(self) -> int:
        return (1 << self.sequence_bits) - 1

    @property
    def max_timestamp(self) -> int:
        return (1 << self.timestamp_bits) - 1

    @classmethod
    def from_settings(cls, settings: Settings) -> SnowflakeLayout:
        return cls(
            epoch_ms=settings.SNOWFLAKE_EPOCH_MS,
            node_id=settings.SNOWFLAKE_NODE_ID,
            node_bits=settings.SNOWFLAKE_NODE_BITS,
            sequence_bits=settings.SNOWFLAKE_SEQUENCE_BITS,
        )


class SnowflakeGenerator:
    """Generates monotonic, collision free 64 bit identifiers.

    Sequence values are handed out inside the same millisecond; when the
    sequence is exhausted the generator waits for the next millisecond instead
    of returning a duplicate. A wall clock that moves backwards never produces a
    smaller identifier: the generator keeps issuing from the last observed
    timestamp.
    """

    def __init__(self, layout: SnowflakeLayout) -> None:
        self._layout = layout
        self._lock = threading.Lock()
        self._last_timestamp_ms = 0
        self._sequence = 0

    @property
    def layout(self) -> SnowflakeLayout:
        return self._layout

    def _current_timestamp_ms(self) -> int:
        return int(time.time() * 1000)

    def next_id(self) -> int:
        """Return the next identifier."""
        with self._lock:
            timestamp_ms = self._current_timestamp_ms() - self._layout.epoch_ms
            if timestamp_ms < 0:
                raise ValueError("SNOWFLAKE_EPOCH_MS is in the future")
            if timestamp_ms > self._layout.max_timestamp:
                raise ValueError("Snowflake timestamp field overflowed")

            if timestamp_ms > self._last_timestamp_ms:
                self._last_timestamp_ms = timestamp_ms
                self._sequence = 0
            elif timestamp_ms == self._last_timestamp_ms:
                if self._sequence >= self._layout.max_sequence:
                    self._wait_next_millisecond()
                    timestamp_ms = self._current_timestamp_ms() - self._layout.epoch_ms
                    self._last_timestamp_ms = timestamp_ms
                    self._sequence = 0
                else:
                    self._sequence += 1
            else:
                # The clock moved backwards: keep the previous timestamp so the
                # identifier sequence stays monotonic.
                timestamp_ms = self._last_timestamp_ms
                if self._sequence >= self._layout.max_sequence:
                    self._wait_next_millisecond()
                    timestamp_ms = self._current_timestamp_ms() - self._layout.epoch_ms
                    if timestamp_ms < self._last_timestamp_ms:
                        timestamp_ms = self._last_timestamp_ms
                    self._last_timestamp_ms = timestamp_ms
                    self._sequence = 0
                else:
                    self._sequence += 1

            return (
                (timestamp_ms << (self._layout.node_bits + self._layout.sequence_bits))
                | (self._layout.node_id << self._layout.sequence_bits)
                | self._sequence
            )

    def _wait_next_millisecond(self) -> None:
        """Block until the wall clock advances past the last used millisecond."""
        deadline = self._last_timestamp_ms + self._layout.epoch_ms
        while int(time.time() * 1000) <= deadline:
            time.sleep(0.0005)


def build_generator(settings: Settings | None = None) -> SnowflakeGenerator:
    """Build a generator from the process configuration."""
    return SnowflakeGenerator(SnowflakeLayout.from_settings(settings or get_settings()))


_GENERATOR: SnowflakeGenerator | None = None
_GENERATOR_LOCK = threading.Lock()


def new_id() -> int:
    """Return the next snowflake id using the process wide generator."""
    global _GENERATOR
    generator = _GENERATOR
    if generator is None:
        with _GENERATOR_LOCK:
            if _GENERATOR is None:
                _GENERATOR = build_generator()
            generator = _GENERATOR
    return generator.next_id()
