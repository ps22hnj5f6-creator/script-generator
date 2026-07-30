#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日 15:00（北京时间）拉取三源热榜，归一化后写入 hotlist.json。
数据源（用户指定）：
  1. 抖音热点榜 —— 筛选其中财经相关条目
  2. 爱股票 24h 热门要闻
  3. 36氪 24小时热榜
每个源独立 try/except，单个源失败不影响其他源。
主页视频"无时效常青内容"由运营生成时选类型决定，本脚本只负责时效性热榜。
"""
import urllib.request
import urllib.parse
import json
import re
import datetime

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

ITEMS = []

# 抖音热点榜 → 只保留与财经/股市相关的条目
FINANCE_KEYWORDS = ["股", "A股", "美股", "港股", "基金", "财经", "央行", "美联储",
                    "经济", "GDP", "通胀", "降息", "加息", "汇率", "人民币", "美元",
                    "上市", "IPO", "融资", "投资", "理财", "黄金", "原油", "券商",
                    "白酒", "新能源", "半导体", "光伏", "储能", "科技", "营收",
                    "利润", "业绩", "退市", "证监会", "监管", "债", "楼市", "房价",
                    "消费", "企业", "公司", "ChatGPT", "AI", "算力", "锂", "稀土"]


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


# 1) 抖音热点榜（筛选财经相关）
try:
    d = get_json("https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/")
    for it in d.get("word_list", [])[:50]:
        w = it.get("word") or ""
        if any(k in w for k in FINANCE_KEYWORDS):
            # 抖音热榜无原文链接，提供抖音搜索链接方便核实
            link = "https://www.douyin.com/search/" + urllib.parse.quote(w)
            add("抖音热点榜", w, "抖音财经", link)
except Exception as e:
    print("抖音热点榜 失败:", e)

# 2) 爱股票 24h 热门要闻
try:
    ok = False
    for ep in [
        "https://www.aigupiao.com/api/news/hot?type=24h",
        "https://www.aigupiao.com/api/article/hot",
    ]:
        try:
            d = get_json(ep)
            news = (d.get("data", {}).get("list")
                    or d.get("data")
                    or d.get("list")
                    or d.get("items") or [])
            for it in news[:15]:
                t = (it.get("title") or it.get("content") or it.get("name") or "").strip()
                u = (it.get("url") or it.get("link") or it.get("article_url") or "").strip()
                if t:
                    add("爱股票", t, "爱股票要闻", u)
            if news:
                ok = True
                break
        except Exception:
            continue
    if not ok:
        raise Exception("爱股票所有端点均失败")
except Exception as e:
    print("爱股票 失败:", e)

# 3) 36氪 24小时热榜（优先 API，失败则抓首页）
try:
    ok = False
    try:
        d = get_json("https://36kr.com/api/newsflash")
        for it in (d.get("data", {}).get("items") or [])[:15]:
            t = (it.get("title") or it.get("content") or "").strip()
            u = (it.get("item_url") or it.get("url") or it.get("news_url") or "").strip()
            # 36氪快讯链接转绝对地址
            if u and not u.startswith("http"):
                u = "https://36kr.com" + u
            if t:
                add("36氪", t, "36氪热榜", u)
        ok = True
    except Exception:
        pass
    if not ok:
        html = get_text("https://36kr.com/")
        titles = re.findall(r'class="[^"]*article-item-title[^"]*"[^>]*>(.*?)</a>', html)
        for t in titles[:15]:
            t = re.sub(r"<[^>]+>", "", t).strip()
            if t:
                add("36氪", t, "36氪热榜")
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
