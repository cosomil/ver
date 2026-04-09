from datetime import datetime


def next_version(current_ver: str | None = None) -> str:
    """
    現在時刻から、calver形式の次のバージョンを生成する。
    """
    now = datetime.now()
    date_part = now.strftime("%Y.%m.%d")
    if current_ver is None:
        return f"{date_part}.0"
    try:
        current_date_part, seq_part = current_ver.rsplit(".", 1)
        if current_date_part == date_part:
            seq = int(seq_part) + 1
            return f"{date_part}.{seq}"
    except ValueError:
        pass
    return f"{date_part}.0"
