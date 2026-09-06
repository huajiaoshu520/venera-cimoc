import json
import re
from pathlib import Path


ROOT = Path.cwd()

SOURCE_DIRS = [
    ROOT / "官方",
    ROOT / "三方",
]

OUTPUT_FILE = ROOT / "index.json"


def get_string(text, key):
    """
    从 JS 中读取：

    name: "xxx"
    key: "xxx"
    version: "1.0.0"
    description: "xxx"
    url: "https://xxx"
    """

    pattern = rf"""["']?{re.escape(key)}["']?\s*:\s*["'](.*?)["']"""

    match = re.search(pattern, text, re.S)

    if match:
        return match.group(1).strip()

    return None


def get_value(text, key):
    """
    同时支持：

    key: "xxx"
    key: 'xxx'
    key: `xxx`
    """

    patterns = [
        rf"""["']?{re.escape(key)}["']?\s*:\s*"([^"]*)"""",
        rf"""["']?{re.escape(key)}["']?\s*:\s*'([^']*)'""",
        rf"""["']?{re.escape(key)}["']?\s*:\s*`([^`]*)`""",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.S)

        if match:
            return match.group(1).strip()

    return None


def parse_js(file_path):

    text = file_path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    name = get_value(text, "name")
    key = get_value(text, "key")
    version = get_value(text, "version")
    description = get_value(text, "description")
    url = get_value(text, "url")

    # 没有 name 就使用文件名
    if not name:
        name = file_path.stem

    # 没有 key 就使用文件名
    if not key:
        key = file_path.stem

    # 没有 version 就使用 1.0.0
    if not version:
        version = "1.0.0"

    item = {
        "name": name,
        "fileName": file_path.name,
        "key": key,
        "version": version,
    }

    if description:
        item["description"] = description

    if url:
        item["url"] = url

    return item


def unique_name(name, used):

    if name not in used:
        used[name] = 1
        return name

    used[name] += 1

    return f"{name} {used[name]}"


def unique_key(key, used):

    if key not in used:
        used[key] = 1
        return key

    used[key] += 1

    return f"{key}_{used[key]}"


def main():

    print("================================")
    print("开始生成 index.json")
    print("================================")

    items = []

    used_names = {}
    used_keys = {}

    for source_dir in SOURCE_DIRS:

        print()
        print(f"扫描目录：{source_dir}")

        if not source_dir.exists():
            print("目录不存在，跳过")
            continue

        files = sorted(source_dir.glob("*.js"))

        print(f"发现 {len(files)} 个 JS 文件")

        for file_path in files:

            print(f"  -> {file_path}")

            item = parse_js(file_path)

            item["name"] = unique_name(
                item["name"],
                used_names
            )

            item["key"] = unique_key(
                item["key"],
                used_keys
            )

            items.append(item)

    # 确保一定生成文件
    OUTPUT_FILE.write_text(
        json.dumps(
            items,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    print()
    print("================================")
    print(f"生成完成，共 {len(items)} 个配置")
    print(f"文件：{OUTPUT_FILE}")
    print("================================")


if __name__ == "__main__":
    main()
