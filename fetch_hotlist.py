#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热榜抓取库 + 每日快照脚本
================================
5 大数据源（用户指定）：
  1. 抖音热榜 —— 筛选其中财经/股市相关条目
  2. 财联社头条
  3. 36氪 24小时热榜
  4. 微博热搜 —— 社会榜 + 科技榜
  5. 种子账号当日视频标题（由前端手动粘贴，本脚本不自动抓取）

每条归一化为：
  { "source": str, "title": str, "url": str, "time": str, "heat": int }

build_hotlist() 把所有源合并、按 heat 降序、去重、取前 12 条（最爆），
附 fetchedAt（热点获取时间）返回。

用法：
  - 作为库被 server.py 导入： from fetch_hotlist import build_hotlist
  - 作为脚本每日运行： python fetch_hotlist.py  → 写 hotlist.json（兜底快照）
"""

import json
import re
import datetime
import urllib.request
import urllib.parse

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 抖音热点榜 → 只保留与财经/股市相关的条目
FINANCE_KEYWORDS = ["股", "A股", "美股", "港股", "基金", "财经", "央行", "美联储",
                    "经济", "GDP", "通胀", "降息", "加息", "汇率", "人民币", "美元",
                    "上市", "IPO", "融资", "投资", "理财", "黄金", "原油", "券商",
                    "白酒", "新能源", "半导体", "光伏", "储能", "科技", "营收",
                    "利润", "业绩", "退市", "证监会", "监管", "债", "楼市", "房价",
                    "消费", "企业", "公司", "ChatGPT", "AI", "算力", "锂", "稀土",
                    "债券", "期货", "银行", "保险", "地产", "负债", "亏损", "财报",
                    "市值", "涨停", "跌停", "牛市", "熊市", "抄底", "套牢"]


def _get_json(url, timeout=15, headers=None):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "ignore")
    return json.loads(raw)


def _get_text(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _fmt_time(raw):
    """把各种时间格式统一成 'YYYY-MM-DD HH:MM'，无法解析返回 ''。"""
    if not raw:
        return ""
    try:
        # 10位/13位时间戳
        if isinstance(raw, (int, float)):
            s = float(raw)
            if s > 1e12:
                s = s / 1000
            return datetime.datetime.fromtimestamp(s).strftime("%Y-%m-%d %H:%M")
        s = str(raw).strip()
        if s.isdigit():
            v = float(s)
            if v > 1e12:
                v = v / 1000
            return datetime.datetime.fromtimestamp(v).strftime("%Y-%m-%d %H:%M")
        # ISO / 常见字符串
        s2 = s.replace("T", " ").replace("Z", "").strip()
        m = re.match(r"(\d{4}-\d{2}-\d{2})[ \.]?(\d{2}:\d{2})?", s2)
        if m:
            return (m.group(1) + " " + (m.group(2) or "00:00")).strip()
    except Exception:
        pass
    return ""


def _add(items, source, title, url="", time="", heat=0):
    title = (title or "").strip()
    if title and len(title) <= 80:
        try:
            heat = int(heat) if heat else 0
        except Exception:
            heat = 0
        items.append({
            "source": source,
            "title": title,
            "url": (url or "").strip(),
            "time": _fmt_time(time),
            "heat": heat,
        })


# ============================================================
# 1) 抖音热榜（财经筛选）
# ============================================================
def fetch_douyin_finance():
    items = []
    try:
        d = _get_json("https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/")
        for it in d.get("word_list", [])[:60]:
            w = it.get("word") or ""
            if any(k in w for k in FINANCE_KEYWORDS):
                hv = it.get("hot_value") or 0
                link = "https://www.douyin.com/search/" + urllib.parse.quote(w)
                _add(items, "抖音财经", w, link, "", hv)
    except Exception as e:
        print("抖音财经 失败:", e)
    return items


# ============================================================
# 2) 财联社头条
# ============================================================
def fetch_cailianpress():
    items = []
    endpoints = [
        "https://www.cls.cn/api/flash",                      # 快讯
        "https://www.cls.cn/nodeapi/telegraph?refresh=0&num=30",  # 电报
    ]
    for ep in endpoints:
        try:
            d = _get_json(ep)
            # 快讯结构： data.flash_list[] 或 data.list[]
            arr = (d.get("data", {}).get("flash_list")
                   or d.get("data", {}).get("list")
                   or d.get("data", {}).get("items")
                   or d.get("items") or [])
            for it in arr[:20]:
                t = (it.get("title") or it.get("content") or it.get("brief") or "").strip()
                u = (it.get("url") or it.get("link") or "").strip()
                if u and not u.startswith("http"):
                    u = "https://www.cls.cn" + u
                tm = it.get("updated_at") or it.get("time") or it.get("created_at") or ""
                if t:
                    _add(items, "财联社头条", t, u, tm, 0)
            if items:
                break
        except Exception as e:
            print("财联社端点", ep, "失败:", e)
            continue
    # 兜底：直接抓取财联社首页头条（首页含当日真实头条）
    if not items:
        try:
            html = _get_text("https://www.cls.cn/")
            # 抓取形如 <a ... href="/...">标题</a> 的链接文本，过滤长度
            for m in re.finditer(r'<a[^>]*href="(/[^"]+)"[^>]*>([^<]{10,40})</a>', html):
                url, t = m.group(1), m.group(2).strip()
                if t and ("article" in url or re.search(r"/\d{5,}", url)):
                    _add(items, "财联社头条", t, "https://www.cls.cn" + url, "", 0)
                if len(items) >= 15:
                    break
        except Exception as e:
            print("财联社首页抓取失败:", e)
    return items


# ============================================================
# 3) 36氪 24小时热榜
# ============================================================
def fetch_36kr():
    items = []
    try:
        ok = False
        try:
            d = _get_json("https://36kr.com/api/newsflash")
            for it in (d.get("data", {}).get("items") or [])[:20]:
                t = (it.get("title") or it.get("content") or "").strip()
                u = (it.get("item_url") or it.get("url") or "").strip()
                if u and not u.startswith("http"):
                    u = "https://36kr.com" + u
                hv = it.get("heat") or it.get("pv") or 0
                tm = it.get("published_at") or it.get("created_at") or ""
                if t:
                    _add(items, "36氪热榜", t, u, tm, hv)
            ok = True
        except Exception:
            pass
        if not ok:
            html = _get_text("https://36kr.com/")
            titles = re.findall(r'class="[^"]*article-item-title[^"]*"[^>]*>(.*?)</a>', html)
            for t in titles[:15]:
                t = re.sub(r"<[^>]+>", "", t).strip()
                if t:
                    _add(items, "36氪热榜", t, "", "", 0)
    except Exception as e:
        print("36氪 失败:", e)
    return items


# ============================================================
# 4) 微博热搜（社会榜 + 科技榜）
# ============================================================
def fetch_weibo():
    """微博热搜（社会榜 + 科技榜）—— 只保留财经相关条目。
    从热搜总榜中用 FINANCE_KEYWORDS 过滤出财经/股市/经济相关话题，
    确保每条都是可做财经视频选题的内容。"""
    items = []
    try:
        d = _get_json("https://weibo.com/ajax/side/hotSearch",
                      headers={"Referer": "https://weibo.com/",
                               "Accept": "application/json, text/plain, */*"})
        arr = (d.get("data") or {}).get("realtime") or []
        # 按热度降序，逐条筛选财经相关
        arr = sorted(arr, key=lambda x: (x.get("num") or 0), reverse=True)
        count = 0
        for it in arr:
            w = it.get("word") or ""
            # 只保留财经/股市/经济/科技/AI 相关条目（同抖音筛选逻辑）
            if not any(k in w for k in FINANCE_KEYWORDS):
                continue
            num = it.get("num") or it.get("raw_hot") or 0
            if w:
                link = "https://s.weibo.com/weibo?q=" + urllib.parse.quote(w)
                _add(items, "微博热搜", w, link, "", num)
                count += 1
                if count >= 8:
                    break
    except Exception as e:
        print("微博 失败:", e)
    return items


# ============================================================
# 汇总
# ============================================================
def build_hotlist(extra_items=None, top_n=12):
    """合并 4 个自动源，公平分配后按热度排序取 top_n（默认 12 条最爆）。

    策略「每源保底 + 热度排序」：
      - 每个自动源至少取 3 条（有则取，无则跳过）
      - 剩余名额按全局热度降序补满
    种子账号（第 5 源）不参与热度排序，单独返回 seedItems。
    返回 { "fetchedAt": "...", "items": [...top_n 自动源...], "seedItems": [...] }
    """
    # 按源分组
    by_source = {}
    src_name_map = {
        "fetch_douyin_finance": "抖音财经",
        "fetch_cailianpress": "财联社头条",
        "fetch_36kr": "36氪热榜",
        "fetch_weibo": "微博热搜",
    }
    for fn in (fetch_douyin_finance, fetch_cailianpress, fetch_36kr, fetch_weibo):
        try:
            src_items = fn()
        except Exception as e:
            print("源执行异常:", fn.__name__, e)
            src_items = []
        src_name = src_name_map.get(fn.__name__, fn.__name__)
        # 给无热度条目一个基于排名的虚拟热度（确保不全部为0被挤出）
        for rank, it in enumerate(src_items):
            if not (it.get("heat") and it["heat"] > 0):
                it["heat"] = 100000 - rank * 100
        by_source[src_name] = src_items

    # 全局去重（按标题）
    seen_titles = set()
    for name in by_source:
        uniq = []
        for it in by_source[name]:
            if it["title"] not in seen_titles:
                seen_titles.add(it["title"])
                uniq.append(it)
        by_source[name] = uniq

    # 第一步：每源保底取前 3 条
    picked = []
    for name in by_source:
        src = sorted(by_source[name], key=lambda x: x.get("heat", 0), reverse=True)[:3]
        picked.extend(src)

    # 第二步：剩余所有条目合并，按热度降序
    remainder = []
    already_picked = {it["title"] for it in picked}
    for name in by_source:
        for it in by_source[name]:
            if it["title"] not in already_picked:
                remainder.append(it)
    remainder.sort(key=lambda x: x.get("heat", 0), reverse=True)

    # 合并：保底 + 补满到 top_n
    all_items = picked + remainder

    # 最终全局去重（防止跨源重复）
    seen_final, final = set(), []
    for it in all_items:
        if it["title"] not in seen_final:
            seen_final.add(it["title"])
            final.append(it)

    top = final[:top_n]

    # 种子账号（第 5 源）：手动补充，单独成组
    seed = []
    if extra_items:
        for line in extra_items:
            line = (line or "").strip()
            if line:
                seed.append({"source": "种子账号", "title": line, "url": "",
                             "time": "", "heat": 0})

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return {"fetchedAt": now, "items": top, "seedItems": seed}


# ============================================================
# 每日快照（GitHub Actions 调用）：写 hotlist.json 作为兜底
# ============================================================
if __name__ == "__main__":
    data = build_hotlist()
    with open("hotlist.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    srcs = "/".join(sorted({i["source"] for i in data["items"]})) or "无"
    print(f"写入 hotlist.json：共 {len(data['items'])} 条，来源={srcs}，获取时间={data['fetchedAt']}")
