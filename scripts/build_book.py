# -*- coding: utf-8 -*-
"""诗词/成语类源 Markdown -> 印刷级 PDF 的「源 HTML」(book.html)

这是「诗词成语类电子资料 + 配套 PWA 学习小工具」产品流水线的第 3 步（PDF 半）。
第 4 步用 scripts/render_pdf.js 把 book.html 渲染成真实 PDF。

用法:
  python build_book.py <源.md> <输出book.html> [图片目录]
示例:
  python build_book.py "D:/WorkBuddy-CQ/300首唐诗.md" "D:/WorkBuddy-CQ/book.html" "D:/WorkBuddy-CQ/images"

产物结构（book.html）:
  封面(标题+导语) -> 每卷「卷首图 + 卷名 + 引言 + 收录数」 -> 该卷词卡流(自动分页) -> 结尾页
  @page 尺寸/边距在文件末尾 CSS 的 @page 里控制（默认 A4）。

依赖: Python3 + pypinyin  (pip install pypinyin)

⚠ 多音字硬伤铁律（交付前必查）:
  pypinyin 自动注音对多音字极易读错（如"似"误 shì、"重"误 zhòng、"还"误 hái、
  "行"误 xíng、"藉"误 jí）。任何带拼音的交付物，必须自建「多音字纠错表」覆盖自动结果。
  下面 PINYIN_OVERRIDE 是示例（取自《600个绝美的诗词成语》审校），新项目务必
  按新词条人工核定，不要原样照搬。脚本优先用此表，查不到才走 pypinyin 自动注音。
"""
import re, os, base64, sys
from pypinyin import pinyin as pinyin_fn, Style

SRC = sys.argv[1] if len(sys.argv) > 1 else r"D:\WorkBuddy-CQ\源文件.md"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"D:\WorkBuddy-CQ\book.html"
IMG = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(SRC), "images")

# ---------- 分类 -> 卷首图 映射（★按产品改）----------
# 分类名必须与源 MD 的 ## 标题去序号/副标题后一致；找不到则回退 cover_img。
def pick_img(name):
    # 本产品 6 分类 → 占位图（vol1-6.jpg，由 gen_placeholder 生成，后续可替换为真实素材）
    table = [("寓言", "vol1.jpg"), ("识人", "vol2.jpg"), ("处世", "vol3.jpg"),
             ("成败", "vol4.jpg"), ("祸福", "vol5.jpg"), ("持家", "vol6.jpg")]
    for k, v in table:
        if k in name:
            return v
    return "vol1.jpg"

def short_cat(name):
    n = re.sub(r'^[一二三四五六七八九十]+、', '', name)
    return n.split('·')[0]

def cat_name(h2):
    """## *一、光阴如流水·岁月不等人*  ->  光阴如流水（去 * 斜体 / 序号 / 副标题）"""
    t = h2.replace("##", "").strip()
    t = t.strip("*").strip()
    t = re.sub(r"^[一二三四五六七八九十]+、", "", t)
    if "·" in t:
        t = t.split("·", 1)[0]
    return t.strip()

cover_img = "cover.jpg"


# ---------- 多音字纠错表（★示例，新项目必须按新词条自建）----------
PINYIN_OVERRIDE = {
    # —— 以下为示例条目，演示「键=词条原文(与 .md 中 term 完全一致) → 值=人工核定拼音」——
    "春风又绿江南岸，明月何时照我还": "chūn fēng yòu lǜ jiāng nán àn ， míng yuè hé shí zhào wǒ huán",
    "人生不相见，动如参与商": "rén shēng bù xiāng jiàn ， dòng rú shēn yǔ shāng",
    "千磨万击还坚劲，任尔东西南北风": "qiān mó wàn jī hái jiān jìng ， rèn ěr dōng xī nán běi fēng",
    "居高声自远，非是藉秋风": "jū gāo shēng zì yuǎn ， fēi shì jiè qiū fēng",
    "关关雎鸠，在河之洲。窈窕淑女，君子好逑": "guān guān jū jiū ， zài hé zhī zhōu 。 yǎo tiǎo shū nǚ ， jūn zǐ hǎo qiú",
    "蓬山此去无多路，青鸟殷勤为探看": "péng shān cǐ qù wú duō lù ， qīng niǎo yīn qín wèi tàn kān",
    "朝辞白帝彩云间，千里江陵一日还": "zhāo cí bái dì cǎi yún jiān ， qiān lǐ jiāng líng yī rì huán",
    "知者不惑，仁者不忧，勇者不惧": "zhì zhě bù huò ， rén zhě bù yōu ， yǒng zhě bù jù",
}


def get_pinyin(s):
    if s in PINYIN_OVERRIDE:
        return PINYIN_OVERRIDE[s]
    # 本产品含大量长句民间谚语：长句若走 pypinyin 自动注音，多音字极易读错且拼音冗长无意义。
    # 策略：仅对汉字数 <= 8 的词条（寓言成语/短谚）生成拼音，超长者返回空（不注音）。
    han = re.findall(r'[\u4e00-\u9fff]', s)
    if len(han) > 8:
        return ''
    return ' '.join(p[0] for p in pinyin_fn(s, style=Style.TONE))


def data_img(fn):
    with open(os.path.join(IMG, fn), "rb") as f:
        b = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b}"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- 读取并解析 ----------
text = open(SRC, encoding="utf-8").read()
lines = text.split("\n")
title = ""
intro = []
sections = []
cur = None
active = None
state = "intro"

for ln in lines:
    if ln.startswith("# "):
        title = ln[2:].strip()
        state = "intro"
        continue
    if ln.strip() == "---":
        continue
    if ln.startswith("## "):
        if cur:
            sections.append(cur)
        # 卷名同样走 cat_name 清洗（去 * 斜体 / 序号 / 副标题），避免 PDF 卷首标题出现 *一、xxx* 残星
        cur = {"name": cat_name(ln), "lead": [], "entries": []}
        active = None
        state = "lead"
        continue
    if state == "intro":
        if ln.strip():
            intro.append(ln.strip())
    elif state == "lead":
        if re.match(r"^\*{2,3}【\d+】", ln):
            state = "body"
            m = re.match(r"^\*{2,3}\s*【(\d+)】\s*(.+?)——(.+?)\s*\*{2,3}\s*$", ln)
            if m:
                cur["entries"].append({"n": int(m.group(1)), "term": m.group(2).strip(),
                                        "source": m.group(3).strip(), "desc": ""})
                active = cur["entries"][-1]
        elif ln.strip():
            cur["lead"].append(ln.strip().strip("*"))
    elif state == "body":
        if re.match(r"^\*{2,3}【\d+】", ln):
            m = re.match(r"^\*{2,3}\s*【(\d+)】\s*(.+?)——(.+?)\s*\*{2,3}\s*$", ln)
            if m:
                cur["entries"].append({"n": int(m.group(1)), "term": m.group(2).strip(),
                                        "source": m.group(3).strip(), "desc": ""})
                active = cur["entries"][-1]
        elif not ln.strip():
            active = None
        else:
            if active:
                active["desc"] += ln.strip().strip("*") + " "

if cur:
    sections.append(cur)
print("标题:", title)
print("导语段数:", len(intro))
print("分类数:", len(sections))
for s in sections:
    print("  -", s["name"], "条目:", len(s["entries"]), "引言:", len(s["lead"]))

cover_data = data_img(cover_img)

# ---------- CSS（印刷级水墨风，A4）----------
CSS = """
@page { size: A4; margin: 14mm 14mm 16mm 14mm; }
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --paper: #f4ecd9; --ink: #2b2620; --ink2: #5c5346;
  --seal: #9e2b25; --gold: #a8884e; --line: #c9bca0;
}
html, body {
  background: var(--paper); color: var(--ink);
  font-family: "Songti SC","STSong","SimSun","Noto Serif CJK SC",serif;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
body {
  background-image:
    radial-gradient(circle at 20% 30%, rgba(168,136,78,0.05) 0, transparent 40%),
    radial-gradient(circle at 80% 70%, rgba(158,43,37,0.04) 0, transparent 40%);
}
.page { page-break-after: always; min-height: 256mm; }
.cover { page-break-after: always; height: 264mm; position: relative; overflow: hidden;
  display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
.cover .bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0.16; }
.cover .frame { position: absolute; inset: 14mm; border: 2px solid var(--ink);
  box-shadow: inset 0 0 0 4px var(--paper), inset 0 0 0 5px var(--line); }
.cover .inner { position: relative; z-index: 2; padding: 0 16mm; }
.cover .kicker { color: var(--seal); letter-spacing: 8px; font-size: 15px; margin-bottom: 22px; }
.cover h1 { font-size: 50px; line-height: 1.35; font-weight: 700; letter-spacing: 4px; }
.cover .sub { margin-top: 26px; font-size: 19px; color: var(--ink2); letter-spacing: 2px; }
.cover .seal-big { margin: 40px auto 0; width: 76px; height: 76px; border: 3px solid var(--seal);
  color: var(--seal); border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-family: "Kaiti SC","STKaiti","KaiTi",serif; font-size: 30px; transform: rotate(-4deg); }
.cover .foot { position: absolute; bottom: 22mm; z-index: 2; color: var(--ink2); font-size: 13px; letter-spacing: 3px; }
.sec { page-break-after: always; height: 264mm; display: flex; flex-direction: column; }
.sec img { width: 100%; height: 150mm; object-fit: cover; display: block; border-bottom: 3px solid var(--seal); }
.sec .meta { padding: 12mm 14mm 0; flex: 1; display: flex; flex-direction: column; }
.sec .no { color: var(--seal); font-family: "Kaiti SC","STKaiti","KaiTi",serif; font-size: 16px; letter-spacing: 4px; }
.sec .sname { font-size: 44px; font-weight: 700; letter-spacing: 6px; margin: 8px 0 18px; }
.sec .lead { font-size: 16px; line-height: 2.1; color: var(--ink2); }
.sec .count { margin-top: auto; color: var(--gold); font-family: "Kaiti SC","STKaiti","KaiTi",serif;
  font-size: 15px; letter-spacing: 3px; padding-top: 10mm; }
.cards { display: block; padding-top: 4mm; }
.card { position: relative; border: 1px solid var(--line); padding: 4mm 9mm 4mm 11mm;
  background: rgba(255,252,244,0.6); margin-bottom: 3mm; border-radius: 2px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05); page-break-inside: avoid; }
.card .cat { position: absolute; top: 4mm; right: 10mm; color: var(--line); font-size: 12px; letter-spacing: 2px; }
.card .seal { position: absolute; top: -6px; right: -6px; width: 36px; height: 36px; background: var(--seal);
  color: #fff; border-radius: 4px; transform: rotate(-6deg); display: flex; align-items: center; justify-content: center;
  font-family: "Kaiti SC","STKaiti","KaiTi",serif; font-size: 13px; line-height: 1; text-align: center; }
.card .term { font-size: 28px; font-weight: 700; letter-spacing: 3px; color: var(--ink);
  display: flex; align-items: baseline; flex-wrap: wrap; gap: 10px; }
.card .term .pinyin { font-size: 20px; font-weight: 400; color: var(--ink2); letter-spacing: 1px;
  font-family: "Noto Sans","PingFang SC","Microsoft YaHei",sans-serif; }
.card .source { margin-top: 4px; font-family: "Kaiti SC","STKaiti","KaiTi",serif; font-size: 14px; color: var(--ink2); letter-spacing: 1px; }
.card .source::before { content: "—— "; color: var(--gold); }
.card .desc { margin-top: 6px; font-size: 14px; line-height: 1.75; color: #3a342b; }
.ending { page-break-after: avoid; height: 264mm; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
.ending .big { font-size: 38px; font-weight: 700; letter-spacing: 3px; line-height: 1.6; }
.ending .body { margin-top: 28px; font-size: 17px; line-height: 2.2; color: var(--ink2); max-width: 140mm; }
.ending .seal-big { margin-top: 42px; width: 70px; height: 70px; border: 3px solid var(--seal); color: var(--seal);
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-family: "Kaiti SC","STKaiti","KaiTi",serif; font-size: 28px; transform: rotate(-4deg); }
"""

# ---------- 构建 body ----------
body = []
intro_html = "".join(f"<p>{esc(p)}</p>" for p in intro[:3])
body.append(f"""
<div class="cover">
  <img class="bg" src="{cover_data}">
  <div class="frame"></div>
  <div class="inner">
    <div class="kicker">诗 词 成 语 · 水 墨 珍 藏</div>
    <h1>{esc(title)}</h1>
    <div class="sub">一词一画 · 水墨珍藏</div>
    <div class="seal-big">词<br>韵</div>
  </div>
  <div class="foot">电子书珍藏版 · 敬请静读</div>
</div>
""")

for si, s in enumerate(sections, 1):
    img = pick_img(s["name"])
    img_data = data_img(img)
    lead = "".join(f"<p>{esc(p)}</p>" for p in s["lead"])
    body.append(f"""
<div class="sec">
  <img src="{img_data}">
  <div class="meta">
    <div class="no">第 {si} 卷 · 共 {len(sections)} 卷</div>
    <div class="sname">{esc(s['name'])}</div>
    <div class="lead">{lead}</div>
    <div class="count">本卷收录 {len(s['entries'])} 则 · 以下逐一点评</div>
  </div>
</div>
""")
    cat_short = short_cat(s["name"])
    cards = []
    for e in s["entries"]:
        seal = f"{e['n']:03d}"
        term = esc(e["term"])
        py = esc(get_pinyin(e["term"]))
        src = esc(e["source"])
        desc = esc(e["desc"].strip())
        cards.append(f"""
    <div class="card">
      <div class="cat">{esc(cat_short)}</div>
      <div class="seal">{seal}</div>
      <div class="term">{term}<span class="pinyin">{py}</span></div>
      <div class="source">{src}</div>
      <div class="desc">{desc}</div>
    </div>""")
    body.append(f'<div class="cards">{"".join(cards)}</div>')

body.append(f"""
<div class="ending">
  <div class="big">六百年诗心<br>藏于此卷</div>
  <div class="body">愿这一卷水墨，陪你走过每一个想用美来说话的瞬间。</div>
  <div class="seal-big">终</div>
</div>
""")

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
{''.join(body)}
</body>
</html>"""

open(OUT, "w", encoding="utf-8").write(html)
print("\n已生成:", OUT, "大小:", os.path.getsize(OUT) // 1024, "KB")
print("总条目:", sum(len(s['entries']) for s in sections))
