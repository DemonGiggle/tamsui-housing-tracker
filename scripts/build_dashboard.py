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
    vals = [float(v) for v in values if isinstance(v, (int, float)) and v > 0]
    if not vals:
        return 0
    return sum(vals) / len(vals)


def median(values):
    vals = sorted(float(v) for v in values if isinstance(v, (int, float)) and v > 0)
    if not vals:
        return 0
    n = len(vals)
    mid = n // 2
    if n % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2


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


def svg_line_chart(series_map, title, y_label='萬/坪'):
    width = 900
    height = 320
    margin = {'left': 56, 'right': 24, 'top': 24, 'bottom': 44}
    all_months = sorted({point['month'] for points in series_map.values() for point in points})
    all_vals = [point['avg_unit_price'] for points in series_map.values() for point in points if point['avg_unit_price'] > 0]
    if not all_months or not all_vals:
        return '<div class="card muted">目前沒有足夠資料可畫圖。</div>'
    min_y = min(all_vals)
    max_y = max(all_vals)
    if min_y == max_y:
        min_y -= 1
        max_y += 1
    plot_w = width - margin['left'] - margin['right']
    plot_h = height - margin['top'] - margin['bottom']

    def x_of(idx):
        if len(all_months) == 1:
            return margin['left'] + plot_w / 2
        return margin['left'] + (idx / (len(all_months) - 1)) * plot_w

    def y_of(v):
        return margin['top'] + (max_y - v) / (max_y - min_y) * plot_h

    colors = ['#4f46e5', '#059669', '#dc2626', '#d97706', '#0891b2', '#7c3aed', '#65a30d', '#db2777']
    grid = []
    for step in range(5):
        y_val = min_y + (max_y - min_y) * step / 4
        y = y_of(y_val)
        grid.append(f'<line x1="{margin["left"]}" y1="{y:.1f}" x2="{width-margin["right"]}" y2="{y:.1f}" stroke="#e5e7eb" />')
        grid.append(f'<text x="{margin["left"]-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="#6b7280">{y_val:.1f}</text>')

    x_labels = []
    for idx, month in enumerate(all_months):
        x = x_of(idx)
        x_labels.append(f'<text x="{x:.1f}" y="{height-14}" text-anchor="middle" font-size="11" fill="#6b7280">{esc(month)}</text>')

    lines = []
    legends = []
    for i, (label, points) in enumerate(series_map.items()):
        color = colors[i % len(colors)]
        month_to_point = {p['month']: p for p in points}
        coords = []
        dots = []
        for idx, month in enumerate(all_months):
            point = month_to_point.get(month)
            if not point:
                continue
            x = x_of(idx)
            y = y_of(point['avg_unit_price'])
            coords.append(f'{x:.1f},{y:.1f}')
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}"><title>{esc(label)} {esc(month)}: {point["avg_unit_price"]:.2f} 萬/坪 (n={point["sample_count"]})</title></circle>')
        if coords:
            lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{" ".join(coords)}" />')
            lines.extend(dots)
            legends.append(f'<span class="legend-item"><span class="legend-swatch" style="background:{color}"></span>{esc(label)}</span>')

    return f'''
    <div class="card">
      <div class="chart-head">
        <div>
          <h3>{esc(title)}</h3>
          <p class="muted">Y 軸：平均單價（{esc(y_label)}）｜ X 軸：月份</p>
        </div>
        <div class="legend">{"".join(legends)}</div>
      </div>
      <svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="{esc(title)}">
        {''.join(grid)}
        <line x1="{margin['left']}" y1="{height-margin['bottom']}" x2="{width-margin['right']}" y2="{height-margin['bottom']}" stroke="#9ca3af" />
        <line x1="{margin['left']}" y1="{margin['top']}" x2="{margin['left']}" y2="{height-margin['bottom']}" stroke="#9ca3af" />
        {''.join(lines)}
        {''.join(x_labels)}
      </svg>
    </div>
    '''


def main():
    rows = load_json(DATA_PATH, [])
    watchlist = load_json(WATCHLIST_PATH, {'regions': [], 'communities': [], 'layout_types': []})

    for row in rows:
        if not row.get('observed_month') and row.get('observed_at'):
            row['observed_month'] = str(row['observed_at'])[:7]

    by_region = defaultdict(list)
    by_community = defaultdict(list)
    by_layout = defaultdict(list)
    by_community_layout = defaultdict(list)
    by_series = defaultdict(list)
    for row in rows:
        if row.get('region'):
            by_region[row['region']].append(row)
        if row.get('community'):
            by_community[row['community']].append(row)
        layout = row.get('layout_type') or '未分類'
        by_layout[layout].append(row)
        if row.get('community'):
            by_community_layout[(row['community'], layout)].append(row)
            by_series[(row['community'], layout, row.get('observed_month', ''))].append(row)

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
    communities = sorted(by_community)
    for community in communities:
        items = sorted(by_community[community], key=lambda x: x.get('observed_at', ''))
        last = items[-1]
        community_rows.append(
            f"<tr><td>{esc(community)}</td><td>{esc(last.get('region',''))}</td><td>{esc(last.get('layout_type','未分類'))}</td><td>{avg([x.get('unit_price', 0) for x in items]):.2f}</td><td>{len(items)}</td><td>{esc(last.get('observed_at',''))}</td></tr>"
        )

    layout_detail_rows = []
    for community in communities:
        layouts = sorted({r.get('layout_type') or '未分類' for r in by_community[community]})
        for layout in layouts:
            items = sorted(by_community_layout[(community, layout)], key=lambda x: x.get('observed_at', ''))
            last = items[-1]
            layout_detail_rows.append(
                f"<tr data-community=\"{esc(community)}\" data-layout=\"{esc(layout)}\"><td>{esc(community)}</td><td>{esc(layout)}</td><td>{len(items)}</td><td>{avg([x.get('unit_price', 0) for x in items]):.2f}</td><td>{avg([x.get('total_price', 0) for x in items]):.1f}</td><td>{esc(last.get('observed_at',''))}</td><td>{esc(last.get('source',''))}</td></tr>"
            )

    series_rows = []
    series_export = []
    for (community, layout, month), items in sorted(by_series.items()):
        unit_prices = [x.get('unit_price', 0) for x in items]
        total_prices = [x.get('total_price', 0) for x in items]
        sources = ', '.join(sorted({x.get('source', '') for x in items if x.get('source')}))
        series_export.append({
            'community': community,
            'layout_type': layout,
            'month': month,
            'sample_count': len(items),
            'avg_unit_price': round(avg(unit_prices), 2),
            'median_unit_price': round(median(unit_prices), 2),
            'min_unit_price': round(min([v for v in unit_prices if isinstance(v, (int, float)) and v > 0], default=0), 2),
            'max_unit_price': round(max([v for v in unit_prices if isinstance(v, (int, float)) and v > 0], default=0), 2),
            'avg_total_price': round(avg(total_prices), 1),
            'sources': sorted({x.get('source', '') for x in items if x.get('source')})
        })
        series_rows.append(
            f"<tr data-community=\"{esc(community)}\" data-layout=\"{esc(layout)}\"><td>{esc(community)}</td><td>{esc(layout)}</td><td>{esc(month)}</td><td>{len(items)}</td><td>{avg(unit_prices):.2f}</td><td>{median(unit_prices):.2f}</td><td>{min([v for v in unit_prices if isinstance(v,(int,float)) and v > 0], default=0):.2f}</td><td>{max([v for v in unit_prices if isinstance(v,(int,float)) and v > 0], default=0):.2f}</td><td>{avg(total_prices):.1f}</td><td>{esc(sources)}</td></tr>"
        )

    latest_rows = []
    for row in sorted(rows, key=lambda x: x.get('observed_at', ''), reverse=True)[:80]:
        latest_rows.append(
            f"<tr data-community=\"{esc(row.get('community',''))}\" data-layout=\"{esc(row.get('layout_type','未分類'))}\"><td>{esc(row.get('observed_at',''))}</td><td>{esc(row.get('observed_month',''))}</td><td>{esc(row.get('region',''))}</td><td>{esc(row.get('community',''))}</td><td>{esc(row.get('layout_type','未分類'))}</td><td>{row.get('unit_price',0)}</td><td>{row.get('total_price',0)}</td><td>{esc(row.get('source',''))}</td><td>{esc(row.get('raw_hash',''))}</td></tr>"
        )

    watch_community_cards = []
    monaco_sections = []
    chart_blocks = []
    all_layouts = sorted({x.get('layout_type') or '未分類' for x in rows})
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
            focus_names = [name] + nearby
            monaco_series_rows = []
            for nearby_name in nearby:
                stats = summarize_rows(by_community.get(nearby_name, []))
                nearby_rows.append(
                    f"<tr><td>{esc(nearby_name)}</td><td>{stats['count']}</td><td>{stats['avg_unit_price']:.2f}</td><td>{stats['latest'] or '—'}</td><td>{esc(stats['latest_layout'])}</td></tr>"
                )
            for (community, layout, month), items in sorted(by_series.items()):
                if community not in focus_names:
                    continue
                unit_prices = [x.get('unit_price', 0) for x in items]
                monaco_series_rows.append(
                    f"<tr data-community=\"{esc(community)}\" data-layout=\"{esc(layout)}\"><td>{esc(community)}</td><td>{esc(layout)}</td><td>{esc(month)}</td><td>{len(items)}</td><td>{avg(unit_prices):.2f}</td><td>{median(unit_prices):.2f}</td></tr>"
                )

            default_layout = '2房' if '2房' in all_layouts else (all_layouts[0] if all_layouts else '未分類')
            series_map = {}
            for focus_name in focus_names:
                pts = [s for s in series_export if s['community'] == focus_name and s['layout_type'] == default_layout]
                if pts:
                    series_map[focus_name] = pts
            chart_blocks.append(svg_line_chart(series_map, f'摩納哥周邊 {default_layout} 平均單價走勢'))

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
                  <p class=\"muted\">追蹤方向已從單筆物件，改成「社區 × 房型 × 月份」的長期價格序列。</p>
                </div>
              </div>
              <table>
                <thead><tr><th>周邊社區</th><th>樣本數</th><th>平均單價</th><th>最近觀察</th><th>最近房型</th></tr></thead>
                <tbody>{''.join(nearby_rows) or '<tr><td colspan="5">尚無周邊資料</td></tr>'}</tbody>
              </table>
              <h3>摩納哥與周邊社區房型月度序列</h3>
              <table id=\"monaco-series-table\">
                <thead><tr><th>社區</th><th>房型</th><th>月份</th><th>樣本數</th><th>平均單價</th><th>中位單價</th></tr></thead>
                <tbody>{''.join(monaco_series_rows) or '<tr><td colspan="6">尚無月度序列資料</td></tr>'}</tbody>
              </table>
            </section>
            """)

    community_options = ['<option value="">全部社區</option>'] + [f'<option value="{esc(c)}">{esc(c)}</option>' for c in communities]
    layout_options = ['<option value="">全部房型</option>'] + [f'<option value="{esc(l)}">{esc(l)}</option>' for l in all_layouts]

    html = f"""<!doctype html>
<html lang=\"zh-Hant\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>淡水房市追蹤 MVP</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 0; background: #f7f8fb; color: #1f2937; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 20px; }}
    .hero {{ background: white; border-radius: 16px; padding: 20px; box-shadow: 0 6px 18px rgba(0,0,0,.06); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-top: 16px; }}
    .card {{ background: white; border-radius: 14px; padding: 16px; box-shadow: 0 4px 14px rgba(0,0,0,.05); }}
    .focus-card {{ border: 2px solid #6366f1; }}
    .priority-high {{ border: 2px solid #f59e0b; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
    .chip {{ display: inline-block; padding: 6px 10px; border-radius: 999px; background: #eef2ff; font-size: 13px; }}
    .nearby-block {{ margin-top: 12px; }}
    .eyebrow {{ font-size: 12px; color: #6366f1; font-weight: 700; letter-spacing: .04em; margin-bottom: 8px; }}
    .chart-head {{ display:flex; gap:12px; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; }}
    .legend {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
    .legend-item {{ display:inline-flex; align-items:center; gap:6px; font-size:13px; color:#374151; }}
    .legend-swatch {{ width:12px; height:12px; border-radius:999px; display:inline-block; }}
    .chart {{ width:100%; height:auto; margin-top:12px; }}
    .controls {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-top:16px; }}
    .control label {{ display:block; font-size:13px; font-weight:600; margin-bottom:6px; color:#374151; }}
    .control select {{ width:100%; padding:10px 12px; border-radius:10px; border:1px solid #d1d5db; background:white; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 14px; overflow: hidden; margin-top: 16px; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #e5e7eb; font-size: 14px; vertical-align: top; }}
    th {{ background: #eef2ff; }}
    .muted {{ color: #6b7280; }}
    .hidden-row {{ display:none; }}
    @media (max-width: 720px) {{
      .wrap {{ padding: 14px; }}
      th, td {{ font-size: 13px; padding: 8px; }}
      .chart-head {{ flex-direction:column; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"hero\">
      <h1>淡水房市追蹤 MVP</h1>
      <p class=\"muted\">目標：追蹤每個社區、每個房型，在長時間內的價格變化。</p>
      <p>目前觀察區域：{', '.join(esc(x) for x in watchlist.get('regions', []))}</p>
      <p>房型分類：{', '.join(esc(x) for x in watchlist.get('layout_types', []))}</p>
      <p>原始資料筆數：<strong>{len(rows)}</strong></p>
      <p>月度序列筆數：<strong>{len(by_series)}</strong></p>
      <p class=\"muted\">raw 保留原始 observation；真正看趨勢時，用「社區 × 房型 × 月份」聚合。</p>
      <div class=\"controls\">
        <div class=\"control\">
          <label for=\"communityFilter\">篩選社區</label>
          <select id=\"communityFilter\">{''.join(community_options)}</select>
        </div>
        <div class=\"control\">
          <label for=\"layoutFilter\">篩選房型</label>
          <select id=\"layoutFilter\">{''.join(layout_options)}</select>
        </div>
      </div>
    </section>

    {''.join(chart_blocks)}
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
      <h2>社區 × 房型明細</h2>
      <table id=\"layout-detail-table\">
        <thead><tr><th>社區</th><th>房型</th><th>樣本數</th><th>平均單價</th><th>平均總價</th><th>最近觀察</th><th>來源</th></tr></thead>
        <tbody>{''.join(layout_detail_rows) or '<tr><td colspan="7">尚無房型資料</td></tr>'}</tbody>
      </table>
    </section>

    <section>
      <h2>社區 × 房型 × 月份 價格序列</h2>
      <table id=\"series-table\">
        <thead><tr><th>社區</th><th>房型</th><th>月份</th><th>樣本數</th><th>平均單價</th><th>中位單價</th><th>最低單價</th><th>最高單價</th><th>平均總價</th><th>來源</th></tr></thead>
        <tbody>{''.join(series_rows) or '<tr><td colspan="10">尚無月度序列資料</td></tr>'}</tbody>
      </table>
    </section>

    <section>
      <h2>最新原始 observations</h2>
      <table id=\"raw-table\">
        <thead><tr><th>日期</th><th>月份</th><th>區域</th><th>社區</th><th>房型</th><th>單價</th><th>總價</th><th>來源</th><th>raw hash</th></tr></thead>
        <tbody>{''.join(latest_rows) or '<tr><td colspan="9">尚無資料</td></tr>'}</tbody>
      </table>
    </section>

    <section class=\"card\">
      <h2>資料說明</h2>
      <ul>
        <li><strong>community.houseprice.tw</strong>：直接從公開社區頁可讀到的成交/房型資料補錄，可信度高於 baseline。</li>
        <li><strong>public-baseline</strong>：公開頁只拿得到均價、格局範圍或待售價位時，先建立的正式基準資料，方便後續持續覆蓋更新。</li>
        <li>目前摩納哥、托斯卡尼麥迪奇名家、尚海、高第、清淞、荷雅名人館、荷雅時尚館已有多筆公開頁明細；水立方、托斯卡尼翡冷翠仍有部分 baseline 佔比較高，後續會繼續補正。</li>
        <li><strong>raw_hash</strong> 用來避免同一批原始 observation 被重複匯入；重點分析則放在月度聚合後的價格序列。</li>
      </ul>
    </section>
  </div>
  <script>
    const SERIES_DATA = {json.dumps(series_export, ensure_ascii=False)};

    function applyFilters() {{
      const community = document.getElementById('communityFilter').value;
      const layout = document.getElementById('layoutFilter').value;
      document.querySelectorAll('#layout-detail-table tbody tr, #series-table tbody tr, #raw-table tbody tr, #monaco-series-table tbody tr').forEach((row) => {{
        const rowCommunity = row.dataset.community || '';
        const rowLayout = row.dataset.layout || '';
        const okCommunity = !community || rowCommunity === community;
        const okLayout = !layout || rowLayout === layout;
        row.classList.toggle('hidden-row', !(okCommunity && okLayout));
      }});
    }}

    document.getElementById('communityFilter').addEventListener('change', applyFilters);
    document.getElementById('layoutFilter').addEventListener('change', applyFilters);
  </script>
</body>
</html>
"""
    OUT_PATH.write_text(html)
    print(OUT_PATH)


if __name__ == '__main__':
    main()
