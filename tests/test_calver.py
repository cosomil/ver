from datetime import datetime

import pytest

import ver.calver as calver


class FrozenDateTime(datetime):
    @classmethod
    def now(cls) -> "FrozenDateTime":  # type: ignore
        return cls(2026, 4, 9, 12, 34, 56)


@pytest.mark.parametrize(
    ("current_ver", "expected"),
    [
        (None, "2026.04.09.0"),
        ("2026.04.09.7", "2026.04.09.8"),
        ("2026.04.08.7", "2026.04.09.0"),
        ("invalid", "2026.04.09.0"),
        ("2026.04.08.invalid", "2026.04.09.0"),
    ],
)
def test_next_version(monkeypatch, current_ver, expected):
    monkeypatch.setattr(calver, "datetime", FrozenDateTime)

    assert calver.next_version(current_ver) == expected
