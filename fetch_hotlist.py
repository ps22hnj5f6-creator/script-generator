#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日 15:00（北京时间）拉取多源热榜，归一化后写入 hotlist.json。
数据源：微博热搜 / 财联社电报 / 东方财富板块异动 / 新浪财经热点 / 36氪创投。
每个源独立 try/except，单个源失败不影响其他源。
说明：主页视频要求"每天保留一条无时效性内容（股民心理按摩/投资心法）"，
该常青内容由运营在生成时选择对应类型（不依赖热榜），本脚本只负责时效性热榜。
"""
import urllib.request
import json
import re
import datetime

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

ITEMS = []


def get_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def get_text(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def add(source, title, category, url=""):
    title = (title or "").strip()
    if title and len(title) <= 60:
        ITEMS.append({"source": source, "title": title, "category": category, "url": url})


# 1) 微博热搜
try:
    d = get_json("https://weibo.com/ajax/side/hotSearch")
    for it in d.get("data", {}).get("realtime", [])[:15]:
        w = it.get("word") or it.get("note")
        if w:
            add("微博热搜", w, "社会热点")
except Exception as e:
    print("微博热搜 失败:", e)

# 2) 财联社电报（A股快讯）
try:
    d = get_json("https://www.cls.cn/nodeapi/getTelegraphList?app=CailianpressWeb&os=web&sv=7.7.5&num=20&page=0")
    for it in d.get("data", {}).get("data", []):
        t = it.get("title") or it.get("content")
        if t:
            add("财联社", re.sub(r"<[^>]+>", "", t)[:50], "A股快讯", "https://www.cls.cn/telegraph")
except Exception as e:
    print("财联社 失败:", e)

# 3) 东方财富 概念板块涨幅榜（板块异动）
try:
    url = ("https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=15&po=1&np=1"
           "&fltt=2&invt=2&fid=f3&fs=b:BKHQ&fields=f12,f14,f3")
    d = get_json(url)
    for it in d.get("data", {}).get("diff", []):
        name = it.get("f14")
        chg = it.get("f3")
        if name:
            arrow = "涨" if (chg or 0) > 0 else "跌"
            add("东方财富", f"{name} 板块{arrow}{abs(chg) if chg else 0}%", "板块异动")
except Exception as e:
    print("东方财富 失败:", e)

# 4) 新浪财经 热点（best-effort）
try:
    d = get_json("https://finance.sina.com.cn/api/hotnews/?page=1&num=15")
    for it in (d.get("result") or d.get("data") or [])[:15]:
        t = it.get("title") or it.get("content") or it.get("name")
        if t:
            add("新浪财经", t, "财经热点")
except Exception as e:
    print("新浪财经 失败:", e)

# 5) 36氪 创投/科技（best-effort，正则取标题）
try:
    html = get_text("https://36kr.com/")
    titles = re.findall(r'class="[^"]*article-item-title[^"]*"[^>]*>(.*?)</a>', html)
    for t in titles[:15]:
        t = re.sub(r"<[^>]+>", "", t).strip()
        if t:
            add("36氪", t, "创投科技")
except Exception as e:
    print("36氪 失败:", e)

# 去重（按标题）
seen, uniq = set(), []
for it in ITEMS:
    k = it["title"]
    if k not in seen:
        seen.add(k)
        uniq.append(it)
ITEMS = uniq[:40]

out = {
    "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    "items": ITEMS,
}
with open("hotlist.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"写入 hotlist.json，共 {len(ITEMS)} 条（来源："
      + "/".join(sorted({i['source'] for i in ITEMS})) + "）")
