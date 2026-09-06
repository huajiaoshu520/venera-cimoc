import json
import re
from pathlib import Path


ROOT = Path.cwd()

SOURCE_DIRS = [
    ROOT / "官方",
    ROOT / "三方",
]

OUTPUT_FILE = ROOT / "index.json"


def get_value(text, key):
    """
    从 JS 中读取字符串字段。

    支持：
    name: "xxx"
    name: 'xxx'
    name: `xxx`
    """

    key_pattern = re.escape(key)

    patterns = [
        r'["\']?' + key_pattern + r'["\']?\s*:\s*"([^"]*)"',
        r'["\']?' + key_pattern + r'["\']?\s*:\s*\'([^\']*)\'',
        r'["\']?' + key_pattern + r'["\']?\s*:\s*`([^`]*)`',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.S)

        if match:
            return match.group(1).strip()

    return None


def parse_js(file_path):
    """
    解析一个 JS 文件。
    """

    text = file_path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    name = get_value(text, "name")
    key = get_value(text, "key")
    version = get_value(text, "version")
    description = get_value(text, "description")
    url = get_value(text, "url")

    # 没有 name，使用文件名
    if not name:
        name = file_path.stem

    # 没有 key，使用文件名
    if not key:
        key = file_path.stem

    # 没有 version，默认 1.0.0
    if not version:
        version = "1.0.0"

    item = {
        "name": name,
        "fileName": file_path.name,
        "key": key,
        "version": version,
    }

    # 有 description 才添加
    if description:
        item["description"] = description

    # 有 url 才添加
    if url:
        item["url"] = url

    return item


def make_unique_name(name, used_names):
    """
    名称重复：

    漫画源
    漫画源 2
    漫画源 3
    """

    if name not in used_names:
        used_names[name] = 1
        return name

    used_names[name] += 1

    return f"{name} {used_names[name]}"


def make_unique_key(key, used_keys):
    """
    key 重复：

    source
    source_2
    source_3
    """

    if key not in used_keys:
        used_keys[key] = 1
        return key

    used_keys[key] += 1

    return f"{key}_{used_keys[key]}"


def main():

    print("================================")
    print("开始生成 index.json")
    print("================================")

    items = []

    used_names = {}
    used_keys = {}

    for source_dir in SOURCE_DIRS:

        print()
        print(f"扫描目录: {source_dir}")

        if not source_dir.exists():
            print("目录不存在，跳过")
            continue

        js_files = sorted(
            source_dir.glob("*.js")
        )

        print(f"发现 {len(js_files)} 个 JS 文件")

        for file_path in js_files:

            print(f"处理: {file_path.name}")

            item = parse_js(file_path)

            item["name"] = make_unique_name(
                item["name"],
                used_names
            )

            item["key"] = make_unique_key(
                item["key"],
                used_keys
            )

            items.append(item)

    # 生成 index.json
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
    print("生成完成")
    print(f"JS 数量: {len(items)}")
    print(f"输出文件: {OUTPUT_FILE}")
    print("================================")


if __name__ == "__main__":
    main()
