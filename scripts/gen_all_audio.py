# -*- coding: utf-8 -*-
"""用当前词条清单，把 audio/1..N.mp3 全部生成（edge-tts 央视男声）。

这是「诗词成语类电子资料 + 配套 PWA 学习小工具」产品流水线的第 2 步。
必须先跑 build_data.py 产出 data.js / entries.json（或导出 terms.json）。

用法:
  python gen_all_audio.py <词条源> <输出audio目录> [VOICE] [CONCURRENCY]
  - 词条源支持三种: terms.json({id,term}) / entries.json({entries:[...]}) / data.js(window.ENTRIES)
  - VOICE 默认 zh-CN-YunyangNeural（央视男声）
  - CONCURRENCY 默认 6（edge-tts 限速，太高易 ConnectionReset，失败会重试）

示例:
  python gen_all_audio.py "D:/WorkBuddy-CQ/每天进步一点点/data.js" "D:/WorkBuddy-CQ/每天进步一点点/audio"
  python gen_all_audio.py terms.json audio zh-CN-XiaoxiaoNeural 4

环境（重要，否则会 403）:
  - 使用 WorkBuddy 托管 venv 的 python:
      C:/Users/brain/.workbuddy/binaries/python/envs/default/Scripts/python.exe
  - 需装 edge_tts（含 pypinyin 可选）:
      python -m pip install -U edge_tts -i https://pypi.tuna.tsinghua.edu.cn/simple
  - 旧版 edge_tts (如 7.2.x) 会被微软令牌校验拒绝 (HTTP 403)，务必升级到 7.3.1+。

⚠ 音频-词条错位铁律:
  只要源 Markdown 增删/重排过词条，必须重跑本脚本全量重新生成 audio/，
  否则会出现「显示词条A、朗读却是词条B」。生成后记得在 app.js 把 AUDIO_V +1 破缓存。
"""
import sys, os, asyncio, json, re

TERMS_SRC = sys.argv[1] if len(sys.argv) > 1 else "terms.json"
AUDIO_DIR = sys.argv[2] if len(sys.argv) > 2 else "audio"
VOICE = sys.argv[3] if len(sys.argv) > 3 else "zh-CN-YunyangNeural"
CONCURRENCY = int(sys.argv[4]) if len(sys.argv) > 4 else 6
RETRY = 3

os.makedirs(AUDIO_DIR, exist_ok=True)


def load_terms(path):
    if path.endswith(".js"):
        txt = open(path, encoding="utf-8").read()
        m = re.search(r"window\.ENTRIES\s*=\s*(\[.*?\]);", txt, re.S)
        data = json.loads(m.group(1))
        return [{"id": e["id"], "term": e.get("term", "")} for e in data]
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict) and "entries" in data:
        return [{"id": e["id"], "term": e.get("term", "")} for e in data["entries"]]
    return data  # terms.json: [{id, term}]


terms = load_terms(TERMS_SRC)
terms.sort(key=lambda x: x["id"])

import edge_tts  # 放这里：缺依赖时给出明确报错而非启动即崩
semaphore = asyncio.Semaphore(CONCURRENCY)
stats = {"ok": 0, "fail": 0, "skip": 0}
fail_ids = []
lock = asyncio.Lock()


async def gen_one(item):
    tid = item["id"]
    text = (item.get("term") or "").strip()
    path = os.path.join(AUDIO_DIR, f"{tid}.mp3")
    if not text:
        async with lock:
            stats["skip"] += 1
            print(f"[SKIP] id={tid} 空词条", flush=True)
        return
    last_err = None
    for attempt in range(1, RETRY + 1):
        try:
            comm = edge_tts.Communicate(text, VOICE)
            await comm.save(path)
            async with lock:
                stats["ok"] += 1
                if stats["ok"] % 50 == 0:
                    print(f"[PROGRESS] ok={stats['ok']} fail={stats['fail']}", flush=True)
            return
        except Exception as e:
            last_err = e
            await asyncio.sleep(1.5 * attempt)
    async with lock:
        stats["fail"] += 1
        fail_ids.append(tid)
        print(f"[FAIL] id={tid} 文本={text!r} 错误={last_err}", flush=True)


async def main():
    async def runner(item):
        async with semaphore:
            await gen_one(item)
    await asyncio.gather(*[asyncio.create_task(runner(it)) for it in terms])
    print(f"\n=== 完成 === ok={stats['ok']} fail={stats['fail']} skip={stats['skip']}", flush=True)
    if fail_ids:
        print("失败 id:", fail_ids, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
