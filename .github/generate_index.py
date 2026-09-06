import json
import re
from pathlib import Path
from urllib.parse import quote


ROOT = Path.cwd()

SOURCE_DIRS = [
    ("三方", ROOT / "三方"),
    ("官方", ROOT / "官方"),
]

OUTPUT_FILE = ROOT / "index.json"

RAW_BASE_URL = (
    "https://raw.githubusercontent.com/"
    "huajiaoshu520/venera-cimoc/main/"
)


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


def parse_js(file_path, folder_name):
    """
    解析 JS 文件。
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

    # 没有 name
    if not name:
        name = file_path.stem

    # 没有 key
    if not key:
        key = file_path.stem

    # 没有 version
    if not version:
        version = "1.0.0"

    # 使用仓库自己的 Raw URL
    raw_url = (
        RAW_BASE_URL
        + quote(folder_name)
        + "/"
        + quote(file_path.name)
    )

    item = {
        "name": name,
        "url": raw_url,
        "key": key,
        "version": version,
    }

    # 有 description 才添加
    if description:
        item["description"] = description

    return item


def make_unique_name(name, used_names):
    """
    name 重复时自动编号：

    拷贝漫画
    拷贝漫画 2
    拷贝漫画 3
    """

    if name not in used_names:
        used_names[name] = 1
        return name

    used_names[name] += 1

    return f"{name} {used_names[name]}"


def main():

    print("================================")
    print("开始生成 index.json")
    print("================================")

    items = []

    used_names = {}

    for folder_name, source_dir in SOURCE_DIRS:

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

            print(f"处理: {folder_name}/{file_path.name}")

            item = parse_js(
                file_path,
                folder_name
            )

            # 只处理 name 重复
            # key 即使重复也保持原样
            item["name"] = make_unique_name(
                item["name"],
                used_names
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
    print(f"共 {len(items)} 个 JS")
    print(f"输出文件: {OUTPUT_FILE}")
    print("================================")


if __name__ == "__main__":
    main()
