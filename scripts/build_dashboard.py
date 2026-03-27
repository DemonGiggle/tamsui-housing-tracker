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


def esc(value):
    return str(value or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def chip(text):
    return f'<span class="chip">{esc(text)}</span>'


def summarize_rows(items):
    if not items:
        return {
            'count': 0,
            'avg_unit_price': 0,
            'avg_total_price': 0,
            'latest': '',
            'latest_layout': '—',
        }
    latest = sorted(items, key=lambda x: x.get('observed_at', ''))[-1]
    return {
        'count': len(items),
        'avg_unit_price': avg([x.get('unit_price', 0) for x in items]),
        'avg_total_price': avg([x.get('total_price', 0) for x in items]),
        'latest': latest.get('observed_at', ''),
        'latest_layout': latest.get('layout_type', '未分類') or '未分類',
    }


def main():
    rows = load_json(DATA_PATH, [])
    watchlist = load_json(WATCHLIST_PATH, {'regions': [], 'communities': [], 'layout_types': []})

    by_region = defaultdict(list)
    by_community = defaultdict(list)
    by_layout = defaultdict(list)
    for row in rows:
        if row.get('region'):
            by_region[row['region']].append(row)
        if row.get('community'):
            by_community[row['community']].append(row)
        layout = row.get('layout_type') or '未分類'
        by_layout[layout].append(row)

    region_cards = []
    for region in sorted(by_region):
        items = by_region[region]
        region_cards.append(f"""
        <div class=\"card\">
          <h3>{esc(region)}</h3>
          <p>樣本數：{len(items)}</p>
          <p>平均單價：{avg([x.get('unit_price', 0) for x in items]):.2f} 萬/坪</p>
          <p>平均總價：{avg([x.get('total_price', 0) for x in items]):.1f} 萬</p>
        </div>
        """)

    layout_cards = []
    for layout in sorted(by_layout):
        items = by_layout[layout]
        layout_cards.append(f"""
        <div class=\"card\">
          <h3>{esc(layout)}</h3>
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
            f"<tr><td>{esc(community)}</td><td>{esc(last.get('region',''))}</td><td>{esc(last.get('layout_type','未分類'))}</td><td>{avg([x.get('unit_price', 0) for x in items]):.2f}</td><td>{len(items)}</td><td>{esc(last.get('observed_at',''))}</td></tr>"
        )

    latest_rows = []
    for row in sorted(rows, key=lambda x: x.get('observed_at', ''), reverse=True)[:20]:
        latest_rows.append(
            f"<tr><td>{esc(row.get('observed_at',''))}</td><td>{esc(row.get('region',''))}</td><td>{esc(row.get('community',''))}</td><td>{esc(row.get('layout_type','未分類'))}</td><td>{row.get('unit_price',0)}</td><td>{row.get('total_price',0)}</td><td>{esc(row.get('note',''))}</td></tr>"
        )

    watch_community_cards = []
    monaco_sections = []
    for item in watchlist.get('communities', []):
        name = item.get('name', '')
        region = item.get('region', '')
        priority = item.get('priority', '')
        notes = item.get('notes', '')
        nearby = item.get('nearby_communities', [])
        nearby_html = ''.join(chip(x) for x in nearby) or '<span class="muted">尚未補上附近社區</span>'
        watch_community_cards.append(f"""
        <div class=\"card priority-{esc(priority).lower()}\">
          <h3>{esc(name)}</h3>
          <p>區域：{esc(region)}</p>
          <p>優先級：{esc(priority)}</p>
          <p class=\"muted\">{esc(notes)}</p>
          <div class=\"nearby-block\">
            <strong>附近社區：</strong>
            <div class=\"chips\">{nearby_html}</div>
          </div>
        </div>
        """)

        if name == '摩納哥社區':
            core_stats = summarize_rows(by_community.get(name, []))
            nearby_rows = []
            for nearby_name in nearby:
                stats = summarize_rows(by_community.get(nearby_name, []))
                nearby_rows.append(
                    f"<tr><td>{esc(nearby_name)}</td><td>{stats['count']}</td><td>{stats['avg_unit_price']:.2f}</td><td>{stats['latest'] or '—'}</td><td>{esc(stats['latest_layout'])}</td></tr>"
                )
            monaco_sections.append(f"""
            <section>
              <h2>摩納哥社區專區</h2>
              <div class=\"grid\">
                <div class=\"card focus-card\">
                  <div class=\"eyebrow\">核心觀察社區</div>
                  <h3>摩納哥社區</h3>
                  <p>樣本數：<strong>{core_stats['count']}</strong></p>
                  <p>平均單價：<strong>{core_stats['avg_unit_price']:.2f}</strong> 萬/坪</p>
                  <p>平均總價：<strong>{core_stats['avg_total_price']:.1f}</strong> 萬</p>
                  <p>最近觀察：{esc(core_stats['latest'] or '—')}</p>
                  <p>最近房型：{esc(core_stats['latest_layout'])}</p>
                </div>
                <div class=\"card\">
                  <div class=\"eyebrow\">周邊社區池</div>
                  <h3>地理附近社區</h3>
                  <div class=\"chips\">{nearby_html}</div>
                  <p class=\"muted\">先把摩納哥與周邊街廓一起追蹤，之後再慢慢累積成自己的在地資料庫。</p>
                </div>
              </div>
              <table>
                <thead><tr><th>周邊社區</th><th>樣本數</th><th>平均單價</th><th>最近觀察</th><th>最近房型</th></tr></thead>
                <tbody>{''.join(nearby_rows) or '<tr><td colspan="5">尚無周邊資料</td></tr>'}</tbody>
              </table>
            </section>
            """)

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
    .focus-card {{ border: 2px solid #6366f1; }}
    .priority-high {{ border: 2px solid #f59e0b; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
    .chip {{ display: inline-block; padding: 6px 10px; border-radius: 999px; background: #eef2ff; font-size: 13px; }}
    .nearby-block {{ margin-top: 12px; }}
    .eyebrow {{ font-size: 12px; color: #6366f1; font-weight: 700; letter-spacing: .04em; margin-bottom: 8px; }}
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
      <p>目前觀察區域：{', '.join(esc(x) for x in watchlist.get('regions', []))}</p>
      <p>房型分類：{', '.join(esc(x) for x in watchlist.get('layout_types', []))}</p>
      <p>資料筆數：<strong>{len(rows)}</strong></p>
      <p class=\"muted\">重點：每坪單價要搭配房型一起看，也要搭配附近可比社區一起看。</p>
    </section>

    {''.join(monaco_sections)}

    <section>
      <h2>特別觀察建案</h2>
      <div class=\"grid\">{''.join(watch_community_cards) or '<div class="card">目前尚未設定</div>'}</div>
    </section>

    <section>
      <h2>區域概覽</h2>
      <div class=\"grid\">{''.join(region_cards)}</div>
    </section>

    <section>
      <h2>房型概覽</h2>
      <div class=\"grid\">{''.join(layout_cards)}</div>
    </section>

    <section>
      <h2>社區觀察</h2>
      <table>
        <thead><tr><th>社區</th><th>區域</th><th>主要房型</th><th>平均單價</th><th>樣本數</th><th>最近觀察</th></tr></thead>
        <tbody>{''.join(community_rows) or '<tr><td colspan="6">目前還沒有社區資料</td></tr>'}</tbody>
      </table>
    </section>

    <section>
      <h2>最新觀察</h2>
      <table>
        <thead><tr><th>日期</th><th>區域</th><th>社區</th><th>房型</th><th>單價(萬/坪)</th><th>總價(萬)</th><th>備註</th></tr></thead>
        <tbody>{''.join(latest_rows) or '<tr><td colspan="7">尚無資料</td></tr>'}</tbody>
      </table>
    </section>

    <section class=\"card\">
      <h2>下一步建議</h2>
      <ul>
        <li>優先補摩納哥與周邊社區的真實觀察資料</li>
        <li>之後每筆資料都加上房型，讓單價比較更準</li>
        <li>下一版可加「摩納哥 vs 周邊社區」圖表化比較</li>
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
