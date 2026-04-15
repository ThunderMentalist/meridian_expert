from pathlib import Path

from meridian_expert.settings import resolve_paths


def test_resolve_paths_precedence(monkeypatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "repos.local.yaml").write_text(
        "meridian_repo_path: ../local-meridian\nmeridian_aux_repo_path: ../local-aux\nworkspace_path: ./local-runtime\n",
        encoding="utf-8",
    )
    (config_dir / "repos.example.yaml").write_text(
        "meridian_repo_path: ../example-meridian\nmeridian_aux_repo_path: ../example-aux\nworkspace_path: ./example-runtime\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MERIDIAN_REPO_PATH", "../env-meridian")
    monkeypatch.setenv("MERIDIAN_AUX_REPO_PATH", "../env-aux")
    monkeypatch.setenv("MERIDIAN_EXPERT_WORKSPACE", "./env-runtime")

    paths = resolve_paths(cli_meridian="../cli-meridian", cli_aux="../cli-aux", cli_workspace="./cli-runtime")
    assert paths.meridian_repo_path == Path("../cli-meridian")
    assert paths.meridian_aux_repo_path == Path("../cli-aux")
    assert paths.workspace_path == Path("./cli-runtime")


def test_resolve_paths_env_overrides_local(monkeypatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "repos.local.yaml").write_text(
        "meridian_repo_path: ../local-meridian\nmeridian_aux_repo_path: ../local-aux\nworkspace_path: ./local-runtime\n",
        encoding="utf-8",
    )
    (config_dir / "repos.example.yaml").write_text(
        "meridian_repo_path: ../example-meridian\nmeridian_aux_repo_path: ../example-aux\nworkspace_path: ./example-runtime\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MERIDIAN_REPO_PATH", "../env-meridian")
    monkeypatch.setenv("MERIDIAN_AUX_REPO_PATH", "../env-aux")
    monkeypatch.setenv("MERIDIAN_EXPERT_WORKSPACE", "./env-runtime")

    paths = resolve_paths()
    assert paths.meridian_repo_path == Path("../env-meridian")
    assert paths.meridian_aux_repo_path == Path("../env-aux")
    assert paths.workspace_path == Path("./env-runtime")
