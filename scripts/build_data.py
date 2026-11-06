# -*- coding: utf-8 -*-
"""解析诗词/成语类源 Markdown -> 结构化数据 (data.js + entries.json)

这是「诗词成语类电子资料 + 配套 PWA 学习小工具」产品流水线的第 1 步。
源 Markdown 格式见 references/md-format.md。

用法:
  python build_data.py <源.md> <输出目录> [COLLECTION_ID] [COLLECTION_NAME]
示例:
  python build_data.py "D:/WorkBuddy-CQ/300首唐诗.md" "D:/WorkBuddy-CQ/pwa" tang "300首唐诗"

依赖:
  Python 3 + 标准库（无需第三方包）
输出:
  <输出目录>/data.js      前端 <script src="data.js"> 引入，挂 window.ENTRIES / window.COLLECTIONS
  <输出目录>/entries.json  结构化备份，便于其他脚本消费
"""
import sys, re, json, os

SRC = sys.argv[1] if len(sys.argv) > 1 else r"D:\WorkBuddy-CQ\源文件.md"
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else r"D:\WorkBuddy-CQ\pwa"
COLL_ID = sys.argv[3] if len(sys.argv) > 3 else "cy"
COLL_NAME = sys.argv[4] if len(sys.argv) > 4 else "我的诗词成语集"

HAN = re.compile(r"[\u4e00-\u9fff]")

# 词条行: **【编号】词条——出处** 或 ***【编号】词条——出处**（两星/三星均可）
entry_re = re.compile(r"\*{2,3}【(\d+)】(.*?)——(.*?)\*{2,3}")


def cat_name(h2):
    """## *一、光阴如流水·岁月不待人*  ->  光阴如流水"""
    t = h2.replace("##", "").strip()
    t = t.strip("*").strip()                          # 去 Markdown 斜体 * 包裹
    t = re.sub(r"^[一二三四五六七八九十]+、", "", t)  # 去序号 "一、"
    if "·" in t:
        t = t.split("·", 1)[0]                         # 去副标题
    return t.strip()


def main():
    text = open(SRC, encoding="utf-8").read()
    lines = text.split("\n")
    entries = []
    cur_cat = ""
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        if line.startswith("## "):
            cur_cat = cat_name(line)
            i += 1
            continue
        m = entry_re.search(line)
        if m:
            eid = int(m.group(1))
            term = m.group(2).strip()
            source = m.group(3).strip()
            hanchars = HAN.findall(term)
            # 收集释义：后续非空行，直到下一个条目/标题/分隔线
            meaning_lines = []
            j = i + 1
            while j < n:
                nl = lines[j].strip()
                if (nl.startswith("**【") or nl.startswith("***【")
                        or nl.startswith("## ") or nl == "---"):
                    break
                if nl:
                    meaning_lines.append(nl.strip("*"))
                j += 1
            meaning = " ".join(meaning_lines).strip()
            entries.append({
                "id": eid,
                "collection": COLL_ID,
                "term": term,
                "chars": len(hanchars),
                "pinyin": "",
                "source": source,
                "meaning": meaning,
                "category": cur_cat,
            })
            i = j
            continue
        i += 1

    entries.sort(key=lambda e: e["id"])
    ids = [e["id"] for e in entries]
    print("解析条数:", len(entries))
    print("id范围:", ids[0], "~", ids[-1], "连续:", ids == list(range(ids[0], ids[-1] + 1)))
    print("分类数:", len(set(e["category"] for e in entries)))
    print("样例:", json.dumps(entries[0], ensure_ascii=False))

    os.makedirs(OUT_DIR, exist_ok=True)
    collections = [{"id": COLL_ID, "name": COLL_NAME}]
    with open(os.path.join(OUT_DIR, "entries.json"), "w", encoding="utf-8") as f:
        json.dump({"collections": collections, "entries": entries}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "data.js"), "w", encoding="utf-8") as f:
        f.write("// 自动生成，勿手改。前端通过 <script src=\"data.js\"> 引入。\n")
        f.write("window.COLLECTIONS = " + json.dumps(collections, ensure_ascii=False) + ";\n")
        f.write("window.ENTRIES = " + json.dumps(entries, ensure_ascii=False) + ";\n")
    print("已写出", os.path.join(OUT_DIR, "data.js / entries.json"))


if __name__ == "__main__":
    main()
