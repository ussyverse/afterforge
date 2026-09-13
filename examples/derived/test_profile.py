"""Derived profile-resolution regression; synthetic paths, real historical assumption."""

from regression_subject import profile_home


def test_resolved_default_home(tmp_path):
    (tmp_path / "state.db").touch()
    assert (profile_home(tmp_path, "default") / "state.db").is_file(), (
        "resolved home must not append profiles/default"
    )


def test_named_profile_is_already_resolved(tmp_path):
    named = tmp_path / "profiles" / "work"
    named.mkdir(parents=True)
    assert profile_home(named, "work") == named, "respect already resolved named home"
