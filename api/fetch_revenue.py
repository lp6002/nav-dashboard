#!/usr/bin/env python3
"""抓取 IAA 后台（47.237.119.194:8800）所有自投应用的今日广告收益，
写入 api/revenue.json 供前端展示。

执行方式：
  python api/fetch_revenue.py
或由 cronjob 周期调用（建议每 5~10 分钟一次）。
"""
import json
import re
import os
import sys
import tempfile
import urllib.request
import urllib.error
import urllib.parse
from http.cookiejar import CookieJar
from datetime import datetime, timezone, timedelta

BASE = "http://47.237.119.194:8800"
USER = "lipeng"
PWD  = "peng123"
OUT  = os.path.join(os.path.dirname(__file__), "revenue.json")


def _beijing_now():
    """返回 (date_str, time_str, hours_since_midnight) 北京时间"""
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    hours = now.hour + now.minute / 60.0
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), hours


def _login_and_stats(opener, package_names, max_total=20):
    """复用已登录的 opener 并发拉每个包名的 /admin/dashboard/stats
    max_total：全部完成超时（秒）
    """
    import concurrent.futures
    results = {}
    pkg_list = list(package_names)
    def fetch_one(pkg):
        url = f"{BASE}/admin/dashboard/stats?packageNames={urllib.parse.quote(pkg)}"
        try:
            body = opener.open(url, timeout=6).read().decode("utf-8", errors="ignore")
            j = json.loads(body)
            if j.get("code") == 200:
                return pkg, j["data"]
            return pkg, {"error": j.get("message", "未知错误")}
        except Exception as e:
            return pkg, {"error": str(e)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(fetch_one, p) for p in pkg_list]
        # 整体超时用 wait 而非单包，避免一个卡住全部
        done, not_done = concurrent.futures.wait(futs, timeout=max_total)
        for f in done:
            pkg, res = f.result()
            results[pkg] = res
        for f in not_done:
            f.cancel()
    return results


def login():
    """登录拿已认证的 opener（单次登录，后续复用 session）"""
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [("User-Agent", "Mozilla/5.0 (RevenueFetcher/1.0)")]

    html = opener.open(f"{BASE}/login", timeout=10).read().decode("utf-8", errors="ignore")
    m = re.search(r'_csrf" value="([^"]+)"', html)
    if not m:
        raise RuntimeError("登录页未找到 _csrf token")
    csrf = m.group(1)
    data = urllib.parse.urlencode({"_csrf": csrf, "username": USER, "password": PWD}).encode()
    req = urllib.request.Request(f"{BASE}/login", data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    opener.open(req, timeout=10)
    return opener


def fetch_package_list(opener):
    """从 /admin HTML 中提取自投包名列表（带显示名）"""
    try:
        html = opener.open(f"{BASE}/admin", timeout=10).read().decode("utf-8", errors="ignore")
    except Exception as e:
        raise RuntimeError(f"GET /admin 失败: {e}")

    pattern = re.compile(
        r'data-value="([^"]+)"\s+data-text="([^"]+)"\s+data-publisher="([^"]+)"'
    )
    apps = []
    for m in pattern.finditer(html):
        pkg, name, publisher = m.group(1), m.group(2), m.group(3)
        apps.append({"pkg": pkg, "name": name, "publisher": publisher})
    if not apps:
        raise RuntimeError("admin 页面未匹配到任何包名")
    return apps


def main():
    print("[fetch_revenue] 开始抓取...")
    try:
        opener = login()
        apps = fetch_package_list(opener)
    except Exception as e:
        print(f"[fetch_revenue] 拉包名失败 ({e})，使用默认 4 个包名")
        apps = [
            {"pkg": "com.papaogamegirl.album", "name": "自投-泡泡龙001", "publisher": "自投"},
            {"pkg": "com.ballgirlgames.sort",   "name": "自投-球排-合肥", "publisher": "自投"},
            {"pkg": "com.shelfgament.shelf",   "name": "自投-shelf002",  "publisher": "自投"},
            {"pkg": "com.blockabeau.block",    "name": "自投-Block-mv001","publisher": "自投"},
        ]
        opener = login()  # 用默认包名也要重登拿 session
    print(f"[fetch_revenue] 应用数: {len(apps)}")
    print(f"[fetch_revenue] 拉取统计中...")
    stats = _login_and_stats(opener, [a["pkg"] for a in apps])
    print(f"[fetch_revenue] 统计完成 {len(stats)} 条")
    date_str, time_str, hours = _beijing_now()

    rows = []
    for a in apps:
        d = stats.get(a["pkg"], {})
        if "error" in d:
            rows.append({
                "name": a["name"],
                "pkg": a["pkg"],
                "publisher": a["publisher"],
                "revenue": None,
                "predicted": None,
                "error": d["error"],
            })
            continue
        rev = float(d.get("todayAdRevenue") or 0)
        pred = round(rev / hours * 24, 2) if hours > 0 else 0.0
        rows.append({
            "name": a["name"],
            "pkg": a["pkg"],
            "publisher": a["publisher"],
            "revenue": round(rev, 2),
            "predicted": pred,
            "change_rate": d.get("todayAdRevenueChangeRate"),
            "today_new_users": d.get("todayNewUsers"),
            "today_active_users": d.get("todayActiveUsers"),
            "today_ad_count": d.get("todayAdCount"),
        })

    payload = {
        "fetched_at": f"{date_str} {time_str}",
        "fetched_date": date_str,
        "fetched_time": time_str,
        "hours_elapsed": round(hours, 2),
        "formula": "predicted = revenue / hours_elapsed * 24",
        "rows": rows,
    }

    # 原子写：先写 .tmp 再替换，避免读到半截文件
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUT)
    print(f"[fetch_revenue] OK · {len(rows)} 个应用 · 写入 {OUT}")
    print(f"[fetch_revenue] 时间 {date_str} {time_str} · 已过 {hours:.2f}h")
    return 0


if __name__ == "__main__":
    sys.exit(main())
