import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent

SOURCE_DIRS = [
    ROOT / "官方",
    ROOT / "三方",
]

OUTPUT_FILE = ROOT / "index.json"


def remove_comments(text):
    """
    删除 JS 注释，避免简单正则解析时受到注释影响。
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*", "", text)
    return text


def get_string(text, key):
    """
    从 JS 中提取类似：

    name: "爱看漫"
    name: '爱看漫'

    的字段。
    """
    pattern = rf"""
        ['"]?{re.escape(key)}['"]?
        \s*:\s*
        (["'])
        (.*?)
        \1
    """

    match = re.search(pattern, text, re.S | re.X)

    if match:
        return match.group(2).strip()

    return None


def get_name_from_filename(filename):
    """
    没有 name 时，根据文件名生成一个名字。
    """
    return Path(filename).stem


def make_unique_name(name, used_names):
    """
    如果名称重复：

    爱看漫
    爱看漫 2
    爱看漫 3
    ...
    """
    if name not in used_names:
        used_names[name] = 1
        return name

    used_names[name] += 1

    return f"{name} {used_names[name]}"


def make_unique_key(key, used_keys):
    """
    如果 key 重复：

    ikmmh
    ikmmh_2
    ikmmh_3
    ...
    """
    if key not in used_keys:
        used_keys[key] = 1
        return key

    used_keys[key] += 1

    return f"{key}_{used_keys[key]}"


def parse_js(file_path):
    """
    从 JS 文件中提取配置。
    """

    text = file_path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    clean_text = remove_comments(text)

    name = get_string(clean_text, "name")
    key = get_string(clean_text, "key")
    version = get_string(clean_text, "version")
    description = get_string(clean_text, "description")
    url = get_string(clean_text, "url")

    if not name:
        name = get_name_from_filename(file_path.name)

    if not key:
        key = file_path.stem

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


def main():

    items = []

    used_names = {}
    used_keys = {}

    for source_dir in SOURCE_DIRS:

        if not source_dir.exists():
            print(f"目录不存在，跳过：{source_dir}")
            continue

        print(f"扫描目录：{source_dir}")

        for js_file in sorted(source_dir.glob("*.js")):

            print(f"处理：{js_file}")

            item = parse_js(js_file)

            # 名称重复自动编号
            item["name"] = make_unique_name(
                item["name"],
                used_names
            )

            # key 重复自动编号
            item["key"] = make_unique_key(
                item["key"],
                used_keys
            )

            items.append(item)

    # 输出漂亮的 JSON
    OUTPUT_FILE.write_text(
        json.dumps(
            items,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    print()
    print(f"生成完成：{OUTPUT_FILE}")
    print(f"共生成 {len(items)} 个配置")


if __name__ == "__main__":
    main()
