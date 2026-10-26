from patchpilot.workspace import create_fresh_workspace, sha256_file


def test_workspace_is_fresh_and_contains_copies_without_changing_original():
    before = sha256_file()
    first = create_fresh_workspace()
    second = create_fresh_workspace()

    assert first.path != second.path
    assert first.workspace_id != second.workspace_id
    assert (first.path / "buggy_discount.py").is_file()
    assert (first.path / "tests" / "test_discount.py").is_file()
    assert sha256_file() == before
