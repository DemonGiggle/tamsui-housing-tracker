#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'observations.json'
WATCHLIST_PATH = ROOT / 'data' / 'watchlist.json'
OUT_PATH = ROOT / 'docs' / 'index.html'


def load_json(path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text())


def avg(values):
    vals = [v for v in values if isinstance(v, (int, float)) and v > 0]
    if not vals:
        return 0
    return sum(vals) / len(vals)


def main():
    rows = load_json(DATA_PATH, [])
    watchlist = load_json(WATCHLIST_PATH, {'regions': [], 'communities': []})

    by_region = defaultdict(list)
    by_community = defaultdict(list)
    for row in rows:
        if row.get('region'):
            by_region[row['region']].append(row)
        if row.get('community'):
            by_community[row['community']].append(row)

    region_cards = []
    for region in sorted(by_region):
        items = by_region[region]
        region_cards.append(f"""
        <div class=\"card\">
          <h3>{region}</h3>
          <p>樣本數：{len(items)}</p>
          <p>平均單價：{avg([x.get('unit_price', 0) for x in items]):.2f} 萬/坪</p>
          <p>平均總價：{avg([x.get('total_price', 0) for x in items]):.1f} 萬</p>
        </div>
        """)

    community_rows = []
    for community in sorted(by_community):
        items = by_community[community]
        last = items[-1]
        community_rows.append(
            f"<tr><td>{community}</td><td>{last.get('region','')}</td><td>{avg([x.get('unit_price', 0) for x in items]):.2f}</td><td>{len(items)}</td><td>{last.get('observed_at','')}</td></tr>"
        )

    latest_rows = []
    for row in sorted(rows, key=lambda x: x.get('observed_at', ''), reverse=True)[:20]:
        latest_rows.append(
            f"<tr><td>{row.get('observed_at','')}</td><td>{row.get('region','')}</td><td>{row.get('community','')}</td><td>{row.get('unit_price',0)}</td><td>{row.get('total_price',0)}</td><td>{row.get('note','')}</td></tr>"
        )

    html = f"""<!doctype html>
<html lang=\"zh-Hant\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>淡水房市追蹤 MVP</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 0; background: #f7f8fb; color: #1f2937; }}
    .wrap {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
    .hero {{ background: white; border-radius: 16px; padding: 20px; box-shadow: 0 6px 18px rgba(0,0,0,.06); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-top: 16px; }}
    .card {{ background: white; border-radius: 14px; padding: 16px; box-shadow: 0 4px 14px rgba(0,0,0,.05); }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 14px; overflow: hidden; margin-top: 16px; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #e5e7eb; font-size: 14px; }}
    th {{ background: #eef2ff; }}
    .muted {{ color: #6b7280; }}
    code {{ background: #eef2ff; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"hero\">
      <h1>淡水房市追蹤 MVP</h1>
      <p class=\"muted\">先把資料累積起來，再慢慢長成長期走勢圖、社區比較、提醒系統。</p>
      <p>目前觀察區域：{', '.join(watchlist.get('regions', []))}</p>
      <p>資料筆數：<strong>{len(rows)}</strong></p>
      <p class=\"muted\">資料來源目前以手動觀察為主；後續可接實價登錄、售屋平台、社區追蹤。</p>
    </section>

    <section>
      <h2>區域概覽</h2>
      <div class=\"grid\">{''.join(region_cards)}</div>
    </section>

    <section>
      <h2>社區觀察</h2>
      <table>
        <thead><tr><th>社區</th><th>區域</th><th>平均單價</th><th>樣本數</th><th>最近觀察</th></tr></thead>
        <tbody>{''.join(community_rows) or '<tr><td colspan="5">目前還沒有社區資料</td></tr>'}</tbody>
      </table>
    </section>

    <section>
      <h2>最新觀察</h2>
      <table>
        <thead><tr><th>日期</th><th>區域</th><th>社區</th><th>單價(萬/坪)</th><th>總價(萬)</th><th>備註</th></tr></thead>
        <tbody>{''.join(latest_rows) or '<tr><td colspan="6">尚無資料</td></tr>'}</tbody>
      </table>
    </section>

    <section class=\"card\">
      <h2>下一步建議</h2>
      <ul>
        <li>先補你的觀察社區名單到 <code>data/watchlist.json</code></li>
        <li>每週手動補幾筆觀察資料，先把樣本養起來</li>
        <li>下一版再加月度走勢圖、異常價格提醒、來源欄位細分</li>
      </ul>
    </section>
  </div>
</body>
</html>
"""
    OUT_PATH.write_text(html)
    print(OUT_PATH)


if __name__ == '__main__':
    main()
