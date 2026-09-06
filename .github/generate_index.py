import json
import re
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path.cwd()

OFFICIAL_DIR = ROOT / "官方"
THIRD_PARTY_DIR = ROOT / "三方"
OUTPUT_FILE = ROOT / "index.json"

RAW_BASE_URL = (
    "https://cdn.jsdelivr.net/gh/"
    "huajiaoshu520/venera-cimoc@main/"
)

OFFICIAL_INDEX_URL = (
    "https://raw.githubusercontent.com/"
    "venera-app/venera-configs/main/index.json"
)


# 三方源如果需要特殊名称 / key / version，
# 可以在这里覆盖。
#
# 注意：
# key 重复是允许的，不会自动修改 key。
THIRD_PARTY_OVERRIDES = {
    "51manga.js": {
        "name": "51漫画",
        "key": "51manga",
        "version": "1.0.0",
    },
    "bilimanga.js": {
        "name": "嗶哩漫畫",
        "key": "bilimanga",
        "version": "1.2.0",
    },
    "rumanhua.js": {
        "name": "如漫画",
        "key": "rumanhua",
        "version": "1.0.0",
    },
    "zerobyw33.js": {
        "name": "zero搬运网",
        "key": "zerobyw33",
        "version": "1.2.0",
    },
}


def raw_url(folder_name, file_name):
    """
    生成当前仓库的 Raw URL。

    例如：
    官方/copy_manga.js
    ->
    https://raw.githubusercontent.com/huajiaoshu520/venera-cimoc/main/%E5%AE%98%E6%96%B9/copy_manga.js
    """
    return (
        RAW_BASE_URL
        + quote(folder_name, safe="")
        + "/"
        + quote(file_name, safe="")
    )


def load_official_index():
    """
    读取 Venera 官方仓库自己的 index.json。

    不再从官方 JS 中猜 name/key/version。
    """
    print("正在读取官方 Venera index.json...")

    request = Request(
        OFFICIAL_INDEX_URL,
        headers={
            "User-Agent": "venera-cimoc-index-generator"
        },
    )

    with urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    if not isinstance(data, list):
        raise ValueError("官方 index.json 格式不是数组")

    print(f"官方 index.json 共 {len(data)} 条")

    return data


def build_official_items():
    """
    根据官方 index.json + 本地 官方/ 文件生成数据。

    只收录本地实际存在的 JS。
    """
    official_index = load_official_index()

    local_files = {
        path.name
        for path in OFFICIAL_DIR.glob("*.js")
    }

    items = []

    for entry in official_index:
        file_name = entry.get("fileName")

        if not file_name:
            continue

        # 官方 index 里有，但本地没有，不收录
        if file_name not in local_files:
            continue

        item = {
            "name": entry.get("name") or Path(file_name).stem,
            "url": raw_url("官方", file_name),
            "key": entry.get("key") or Path(file_name).stem,
            "version": entry.get("version") or "1.0.0",
        }

        description = entry.get("description")

        if description:
            item["description"] = description

        items.append(item)

    # 本地有 JS，但官方 index 没有记录
    indexed_files = {
        entry.get("fileName")
        for entry in official_index
        if entry.get("fileName")
    }

    for path in sorted(OFFICIAL_DIR.glob("*.js")):
        if path.name in indexed_files:
            continue

        # 这两个不是漫画源，不加入 index
        if path.name in {"_template_.js", "_venera_.js"}:
            print(
                f"跳过官方辅助文件: {path.name}"
            )
            continue

        print(
            f"警告：官方 index.json 没有找到 {path.name}"
        )

    return items


def extract_class_metadata(text):
    """
    从三方 JS 的 ComicSource class 中提取真正的源元数据。

    只寻找 class 中这种形式：

        name = "51漫画";
        key = "manga51";
        version = "1.1.0";

    不会读取 category.parts[].name、
    Comic 对象里的 name、
    搜索参数里的 name 等内部字段。
    """

    # 先找到 ComicSource 派生 class
    class_match = re.search(
        r"class\s+[A-Za-z_$][\w$]*\s+extends\s+ComicSource\s*\{",
        text,
    )

    if not class_match:
        return {}

    class_start = class_match.start()

    # 只看 class 声明附近的内容。
    # 元数据通常就在 class 开头。
    header = text[
        class_start:
        class_start + 6000
    ]

    def get_class_field(field):
        patterns = [
            rf"\b{re.escape(field)}\s*=\s*(['\"])(.*?)\1\s*;",
            rf"\b{re.escape(field)}\s*=\s*`([^`]*)`\s*;",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                header,
                re.S,
            )

            if match:
                if match.lastindex >= 2:
                    return match.group(2).strip()
                return match.group(1).strip()

        return None

    return {
        "name": get_class_field("name"),
        "key": get_class_field("key"),
        "version": get_class_field("version"),
    }


def build_third_party_item(path):
    """
    解析三方 JS。

    优先使用手工覆盖；
    没有覆盖时，从 ComicSource class 的源定义读取。
    """
    override = THIRD_PARTY_OVERRIDES.get(
        path.name,
        {}
    )

    text = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    metadata = extract_class_metadata(text)

    name = (
        override.get("name")
        or metadata.get("name")
        or path.stem
    )

    key = (
        override.get("key")
        or metadata.get("key")
        or path.stem
    )

    version = (
        override.get("version")
        or metadata.get("version")
        or "1.0.0"
    )

    item = {
        "name": name,
        "url": raw_url("三方", path.name),
        "key": key,
        "version": version,
    }

    description = override.get("description")

    if description:
        item["description"] = description

    return item


def make_unique_name(name, used_names):
    """
    只有 name 重复时才编号：

    漫画源
    漫画源 2
    漫画源 3

    key 永远不修改。
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

    if not OFFICIAL_DIR.exists():
        raise FileNotFoundError(
            f"不存在目录：{OFFICIAL_DIR}"
        )

    if not THIRD_PARTY_DIR.exists():
        raise FileNotFoundError(
            f"不存在目录：{THIRD_PARTY_DIR}"
        )

    items = []

    # --------------------------------
    # 三方
    # --------------------------------
    print()
    print("扫描目录：三方")

    third_party_files = sorted(
        THIRD_PARTY_DIR.glob("*.js")
    )

    print(
        f"发现 {len(third_party_files)} 个 JS 文件"
    )

    for path in third_party_files:
        print(f"处理：三方/{path.name}")

        item = build_third_party_item(path)
        items.append(item)

    # --------------------------------
    # 官方
    # --------------------------------
    print()
    print("扫描目录：官方")

    official_items = build_official_items()

    print(
        f"官方收录 {len(official_items)} 个源"
    )

    items.extend(official_items)

    # --------------------------------
    # name 去重
    # --------------------------------
    print()
    print("处理重复 name...")

    used_names = {}

    for item in items:
        original_name = item["name"]

        item["name"] = make_unique_name(
            original_name,
            used_names,
        )

        if item["name"] != original_name:
            print(
                f"name 重复：{original_name}"
                f" -> {item['name']}"
            )

    # --------------------------------
    # 输出
    # --------------------------------
    OUTPUT_FILE.write_text(
        json.dumps(
            items,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("================================")
    print("生成完成")
    print(f"共 {len(items)} 个漫画源")
    print(f"输出文件：{OUTPUT_FILE}")
    print("================================")


if __name__ == "__main__":
    main()
