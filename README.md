# ver

uv + Pythonで開発されるプロジェクトのために、人間可読かつ厳密なバージョン管理を行うための仕様と実装。

## バージョンのフォーマット
[`CalVer`](https://calver.org/)を採用し、新バージョン公開と日付をリンクさせて管理します。

- **`2026.04.09.0`**: 2026年4月9日に公開
- **`2026.04.10.0`**: 2026年4月10日に公開
- **`2026.04.10.1`**: 2026年4月10日に公開（2回目）

## `ver.toml`
プロジェクトのトップレベルに作成する `ver.toml` ファイルにバージョン情報を記録します。

### 記録する情報
`ver.toml`には、バージョン情報の他にバージョンの整合性を検証するためのハッシュ値が記録されます。

- `version`
    - 現在のバージョン
- `sha256`
  - バージョン管理する対象のファイルから計算されたハッシュ値
  - 記録されたハッシュ値と対象のファイルから再計算されたハッシュ値が異なる場合、新しいバージョンを発行しなければならないことを検知することができます

### `ver.toml` の仕様

`ver.toml` は [TOML](https://toml.io/ja/v1.0.0) で記述します。
`name`, `version`, `sha256`は必須項目となり、これらは機械的に管理します。

```toml
# 対象プロジェクトの識別名
name = "example"

# 人が読むためのバージョン文字列
version = "2026.04.09.0"

# ハッシュ対象ファイル群から計算した内容識別子
sha256 = "8f4f5d7d7a0f0c0d..."

# 任意: ハッシュ計算から除外するファイル名のパターン（正規表現）
# 区切り文字は"/"を使用すること
# 省略時は空配列として扱われる
exclude_patterns = ["^dist/", "^coverage\\.xml$"]

# 任意: デフォルトの除外パターンを無効化するフラグ
# 省略時は false として扱われる
no_default_exclude_patterns = false

# 任意: 開発者が任意の追加情報を格納する領域
# 省略時は空テーブルとして扱われる
[meta]
authors = ["John Doe"]
flavor = "garlic"
```

**デフォルトで設定されるハッシュ計算の除外パターン**
- `"^\\.[^/]+$"`
    - プロジェクトトップレベルにある"."から始まるファイル
- `"^tests/"`
    - プロジェクトトップレベルにある"tests"ディレクトリに含まれる全てのファイル
- `"^(README\\.md|AGENTS\\.md|CLAUDE\\.md)$"`
    - プロジェクトトップレベルにある README.md, AGENTS.md, CLAUDE.md
- `"^LICENSE\\.(txt|md|rst)$"`
    - プロジェクトトップレベルにあるライセンス情報

**必ずハッシュ計算から除外されるファイル**
- `.gitignore`でgit管理対象から外れているファイル
    - これらのファイルはバージョン管理対象外となります

**必ずハッシュ計算に含まれるファイル**
- `uv.lock`
    - uvが生成する、プロジェクトの依存関係が記述されたファイル
    - 依存関係を更新する際には、必ずバージョンも更新しなければならない
    - このがいるはgitの管理対象である必要があります

## `ver.toml` の作成、更新、検証
任意項目の編集を除いて、基本的に`ver`コマンドを使用して操作します。

### `ver init`
プロジェクトに新しく `ver.toml` を作成します。

```shell
# カレントディレクトリに ver.toml を作成
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver init

# 対象ディレクトリを指定して作成
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver init path/to/project

# 名前を指定して作成
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver init --name example

# 初期バージョンと sha256 も同時に生成
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver init --version
```

- `--version` を付けない場合
  - `version` と `sha256` は設定されません。コード編集のあとに、後述の`ver update`を実行してください
- `--version` を付ける場合
  - 現在時刻に基づく初期バージョンと、計算された `sha256` が設定されます

### `ver update`
現在の作業ツリーから `sha256` を再計算し、変更があれば `version` を進めて `ver.toml` を更新します。

```shell
# カレントディレクトリの ver.toml を更新
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver update

# 対象ディレクトリを指定して更新
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver update path/to/project
```

- ハッシュ値に変更がない場合
  - `ver.toml` は書き換えられません
- ハッシュ値に変更がある場合
  - `version` が新しいバージョンに更新され、`sha256` も最新値に置き換えられます

### `ver check`
`ver.toml` に記録されている `version` と `sha256` が、現在の作業ツリーと整合しているかを確認します。

```shell
# カレントディレクトリを検証
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver check

# 対象ディレクトリを指定して検証
uvx --from git+https://github.com/cosomil/ver@v0.0.1 ver check path/to/project
```

`ver check` を使うことで、コード変更に合わせたバージョンの更新が正しく行われていることを検証することができます。

## コードから`ver.toml`を読み込む
コードから現在のバージョン情報を取得したいケースでは、`ver`モジュールを利用することができます。

```shell
# ライブラリのインストール
uv add git+https://github.com/cosomil/ver --tag v0.0.1
```

```python
import ver

config = ver.read_config()
print(f"{config.name}:{config.version}") # example:2026.04.09.0

# metaテーブルも参照可能
meta_data: dict[str, Any] = config.meta
```
