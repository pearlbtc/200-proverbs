# -*- coding: utf-8 -*-
"""反侵权加工：重排 200 条 + 原创化重写全部介绍文字（一次性脚本，保留以便复现）

新编排（自有逻辑，与来源文章的编排明显不同）：
  - 卷序：先 5 卷谚语（识人 -> 处世 -> 成事 -> 祸福 -> 持家），末卷 100 则成语典故收束
  - 卷内：按词条汉字数升序；同字数按首字码位、再按整串码位（确定性、零外部依赖、零事实判断）
  - 主分类名一字不改，兼容 app.js CAT_VOL 与 build_book.py pick_img

注意：重排会改变 id <-> 词条映射，之后必须全量重生成 audio/ 并破缓存。

用法: python scripts/reorder.py [源.md]
执行前自动备份为 备份_源文件_重排前.md
"""
import io, os, re, sys, shutil

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "源文件.md")
BASE = os.path.dirname(SRC)
BACKUP = os.path.join(BASE, "备份_源文件_重排前.md")

TITLE = "# *千古智慧200句，道尽老祖宗的智慧*"

# 顶部导语：平实的编者说明，不吹嘘、不堆金句、不罗列典籍名
INTRO = [
    "这是一本可以随时翻开一页读下去的小书。全书收二百条：一百则为四字成语典故，多可查到典籍出处；"
    "一百句为民间谚语，大多不知最初出自何人之口。两者都是汉语里被反复使用、慢慢沉淀下来的说法。",

    "编排上，先按话题读谚语，再以典故收束。各卷之内不按时代、不按出处，只按字数由短到长排列，"
    "字数相同者以首字字序为次，便于随手翻检。每则附字面释义与一个日常用例，用来疏通字义，不作训诫。",
]

# 主分类名（不可改） -> (新卷序号+副标题, 新卷首引言)
VOLUMES = [
    ("识人辨心", "一、识人辨心·看人与相交",
     "这一卷收二十句关于看人的谚语。民间说人，少讲道理，多讲观察：相处久了才见性情，"
     "境遇变了才见交情。条目不依出处罗列，按字数由短到长编排，同字数者以首字字序为次。"),

    ("处世立身", "二、处世立身·言语与分寸",
     "这一卷收二十句关于分寸的谚语：什么话宜少说，什么事该留余地，怎样与人长久相处。"
     "谚语给的是经验，不是定律，读时不妨对照自己的处境。卷内按字数由短到长编排。"),

    ("成败奋斗", "三、成败奋斗·工夫与积累",
     "这一卷收二十句关于做事的谚语，多讲积累与耐性：工夫下在哪里，收成便在哪里。"
     "句中常拿农耕、手艺、起居作比，读来具体，也提醒人别指望一步到位。卷内按字数由短到长编排。"),

    ("祸福人生", "四、祸福人生·得失与起落",
     "这一卷收二十句关于得失的谚语。顺境逆境、吃亏占便宜、平安与风险，都是过日子里绕不开的题目；"
     "前人把这些观察压成短句，语气往往笃定，读时不必句句当作定论。卷内按字数由短到长编排。"),

    ("持家修身", "五、持家修身·日用与心气",
     "这一卷收二十句关于家与自身的谚语：用度、亲长、教子、读书、心气，都是日常里的小事。"
     "这些说法讲的多是长久之计，取其一端即可。卷内按字数由短到长编排。"),

    ("寓言成语", "六、寓言成语·一百则典故",
     "末卷收一百则四字成语典故。这些条目多有典籍可查，背后是一个有人物、有转折的小故事，"
     "最后凝成四个字。每则标注所见典籍，附字面释义与一个日常用例。放在全书最后，"
     "是想让读者读过口语谚语之后，再回头看看同一类经验在书面语里的样子。"
     "卷内不按时代、不按出处，以首字字序排列，便于检索。"),
]

ENTRY_RE = re.compile(r"^\*{2,3}\s*【(\d+)】\s*(.+?)——(.+?)\s*\*{2,3}\s*$")
HAN = re.compile(r"[\u4e00-\u9fff]")


def parse(lines):
    """切成 [(卷主名, [词条块])]; 每个块 = [词条行, 释义行...]，尾部空白已裁掉"""
    vols, cur, block = {}, None, None

    def flush():
        nonlocal block
        if block and cur:
            while block and not block[-1].strip():
                block.pop()
            if block:
                vols[cur].append(block)
        block = None

    for ln in lines:
        if ln.startswith("## "):
            flush()
            t = ln[3:].strip().strip("*").strip()
            t = re.sub(r"^[一二三四五六七八九十]+、", "", t).split("·", 1)[0].strip()
            cur = t
            vols.setdefault(cur, [])
            continue
        if cur is None:
            continue                      # 标题/导语/分隔线，不参与重排
        if ENTRY_RE.match(ln.strip()):
            flush()
            block = [ln.rstrip()]
            continue
        if ln.strip() == "---":
            flush()
            continue
        if block is not None:
            block.append(ln.rstrip())
        # 卷首引言（*...*）在第一个词条之前，此时 block is None，被跳过
    flush()
    return vols


def term_of(block):
    return ENTRY_RE.match(block[0].strip()).group(2).strip()


def sort_key(block):
    t = term_of(block)
    return (len(HAN.findall(t)), ord(t[0]) if t else 0, t)


def main():
    raw = io.open(SRC, encoding="utf-8").read()
    lines = raw.split("\n")
    if not os.path.exists(BACKUP):
        shutil.copyfile(SRC, BACKUP)
        print("已备份:", BACKUP)

    vols = parse(lines)
    total = sum(len(v) for v in vols.values())
    print("解析卷数:", len(vols), " 条目总数:", total)
    assert total == 200, "条目数不是 200，中止"

    old_pos = {}
    for blocks in vols.values():
        for i, b in enumerate(blocks, 1):
            old_pos[term_of(b)] = i

    out = [TITLE, ""]
    for s in INTRO:
        out += ["*" + s + "*", ""]
    out += ["---", ""]

    new_pos, eid = {}, 0
    for main_name, h2, lead in VOLUMES:
        assert main_name in vols, "缺少分类: " + main_name
        blocks = sorted(vols[main_name], key=sort_key)
        out += ["## " + h2, "", "*" + lead + "*", ""]
        for i, b in enumerate(blocks, 1):
            eid += 1
            t = term_of(b)
            new_pos[t] = (main_name, i, eid)
            b[0] = re.sub(r"【\d+】", "【%d】" % eid, b[0], count=1)
            out += b + [""]
        print("  %-8s 新卷序 %s  %3d 条  id %3d~%3d" %
              (main_name, h2[0], len(blocks), eid - len(blocks) + 1, eid))
        out += [""]

    while out and not out[-1].strip():
        out.pop()
    io.open(SRC, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

    moved = sum(1 for t, (_, i, _) in new_pos.items() if old_pos.get(t) != i)
    vol_changed = sum(1 for t, (m, _, e) in new_pos.items()
                      if m == "寓言成语" and e <= 100)
    print("\n重新编号 1~%d 连续: %s" % (eid, eid == 200))
    print("卷内位置发生变化: %d/200 条" % moved)
    print("原卷一(前100)与末卷(后100)结构已互换: %s" % ("是" if vol_changed == 0 else "否"))
    print("已写出:", SRC)


if __name__ == "__main__":
    main()
