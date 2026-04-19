"""
Filter tests — prove the matcher is deterministic, honors excludes, and
handles the empty-interests fallthrough.
"""

from datetime import datetime, timezone

from signal_digest.core import Identity, Interests, Signal
from signal_digest.filter import filter_for


def _sig(title: str, summary: str = "", tags=None) -> Signal:
    return Signal(
        source="x",
        source_label="X",
        title=title,
        url="",
        published_at=datetime.now(timezone.utc),
        summary=summary,
        tags=tags or [],
    )


def test_term_match_case_insensitive():
    ident = Identity(name="Jane", interests=Interests(terms=["attribution"]))
    sigs = [
        _sig("How Attribution Really Works"),
        _sig("Something unrelated"),
    ]
    out = filter_for(sigs, ident)
    assert len(out) == 1
    assert "Attribution" in out[0].title


def test_tag_match():
    ident = Identity(name="Jane", interests=Interests(tags=["release"]))
    sigs = [
        _sig("Release v2", tags=["release"]),
        _sig("Blog post", tags=["essay"]),
    ]
    out = filter_for(sigs, ident)
    assert len(out) == 1


def test_exclude_terms_short_circuit():
    ident = Identity(
        name="Jane",
        interests=Interests(terms=["bitcoin"], exclude_terms=["crypto"]),
    )
    sigs = [
        _sig("Bitcoin crypto news", summary="ignore me"),
        _sig("Bitcoin price analysis", summary="solid report"),
    ]
    out = filter_for(sigs, ident)
    # Both match "bitcoin", but the first gets excluded by "crypto"
    assert len(out) == 1
    assert out[0].title == "Bitcoin price analysis"


def test_empty_interests_admits_everything():
    """
    When no terms and no tags are set, filter is pass-through. This is
    useful when scoping happens entirely inside a source adapter (e.g.,
    the GitHub source already scopes by identity.interests.github_repos).
    """
    ident = Identity(name="Jane", interests=Interests())
    sigs = [_sig("anything"), _sig("something else")]
    out = filter_for(sigs, ident)
    assert len(out) == 2


def test_deterministic():
    ident = Identity(name="Jane", interests=Interests(terms=["foo"]))
    sigs = [_sig("foo bar"), _sig("baz foo qux"), _sig("no match")]
    out1 = filter_for(sigs, ident)
    out2 = filter_for(sigs, ident)
    assert [s.title for s in out1] == [s.title for s in out2]
