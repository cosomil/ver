# ver

uv + Python で開発されるプロジェクト向けに、`pyproject.toml` を使って人間可読かつ厳密なバージョン管理を行うツールです。

## バージョンのフォーマット
[`CalVer`](https://calver.org/) を採用します。

- `2026.04.09.0`: 2026年4月9日に公開
- `2026.04.10.0`: 2026年4月10日に公開
- `2026.04.10.1`: 2026年4月10日に公開（2回目）

## `pyproject.toml` で管理する情報
`ver` は以下のキーを利用します。

- バージョン: `project.name`
- バージョン文字列: `project.version`
- ハッシュ値: `tool.ver.sha256`
- ハッシュ除外パターン: `tool.ver.exclude_patterns`

設定例:

```toml
[project]
name = "example"
version = "2026.04.09.0"

[tool.ver]
sha256 = "8f4f5d7d7a0f0c0d..."
exclude_patterns = [
  '^\\.[^/]+$',
  '^tests/',
  '^(README\\.md|AGENTS\\.md|CLAUDE\\.md)$',
  '^LICENSE\\.(txt|md|rst)$',
]
```

`ver init` が `DEFAULT_EXCLUDE_PATTERNS` を書き込むときは、TOML の基本文字列ではなくエスケープ不要のリテラル文字列として保存します。

## ハッシュ計算の仕様
`sha256` は git 管理ファイルと未追跡ファイルから計算されます。

デフォルト除外パターン:

- `'^\.[^/]+$'`
- `'^tests/'`
- `'^(README\.md|AGENTS\.md|CLAUDE\.md)$'`
- `'^LICENSE\.(txt|md|rst)$'`

常に除外されるファイル:

- `pyproject.toml`
- `.gitignore` により git 管理対象外になっているファイル

常に含まれるファイル:

- `uv.lock`

`uv.lock` は git の管理対象である必要があります。

## コマンド
### `ver init`
対象ディレクトリの `pyproject.toml` を初期化します。`pyproject.toml` が存在しない場合はエラーとなります。

```shell
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver init
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver init path/to/project
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver init --name example
```

- `project.name` をディレクトリ名、または `--name` で指定した値に更新します
- `project.version` をその時点の最新バージョンに更新します
- `tool.ver.sha256` をその時点の最新ハッシュに更新します
- `tool.ver.exclude_patterns` をデフォルト除外パターンで初期化します

### `ver update`
現在の作業ツリーからハッシュを再計算し、`tool.ver.sha256` と異なる場合のみ `project.version` と `tool.ver.sha256` を更新します。

```shell
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver update
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver update path/to/project
```

### `ver check`
現在の作業ツリーからハッシュを再計算し、`project.version` と `tool.ver.sha256` が整合しているか検証します。

```shell
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver check
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver check path/to/project
```

## ライブラリ API

```shell
uv add git+https://github.com/cosomil/ver --tag v0.0.1
```

```python
import ver

proj = ver.read_project()
print(proj.name)
print(proj.version)

ver_cfg = proj.get_tool_config("ver")
if ver_cfg is not None:
    print(ver_cfg["sha256"])
```
