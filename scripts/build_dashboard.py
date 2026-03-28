#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'observations.json'
WATCHLIST_PATH = ROOT / 'data' / 'watchlist.json'
SERIES_CACHE_PATH = ROOT / 'data' / 'series_cache.json'
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


def pct_change(current, previous):
    if not previous:
        return 0
    return ((current - previous) / previous) * 100


def trend_text(value):
    if value > 0.05:
        return '上升'
    if value < -0.05:
        return '下降'
    return '持平'


def signal_class(value):
    if value > 0.05:
        return 'up'
    if value < -0.05:
        return 'down'
    return 'flat'


def calc_series_value(item):
    # 前台不強調平均 / 中位數字眼，但底層仍需穩定代表值來計算趨勢。
    return item.get('median_unit_price') or item.get('avg_unit_price') or 0


def build_trend_summary(series_export, communities, layouts):
    cards = []
    for community in communities:
        for layout in layouts:
            pts = [x for x in series_export if x['community'] == community and x['layout_type'] == layout]
            pts = sorted(pts, key=lambda x: x['month'])
            if len(pts) < 2:
                continue
            latest = pts[-1]
            latest_val = calc_series_value(latest)
            prev_1 = calc_series_value(pts[-2]) if len(pts) >= 2 else 0
            prev_3 = calc_series_value(pts[-4]) if len(pts) >= 4 else 0
            prev_6 = calc_series_value(pts[-7]) if len(pts) >= 7 else 0
            mom = pct_change(latest_val, prev_1) if prev_1 else 0
            qoq = pct_change(latest_val, prev_3) if prev_3 else 0
            half = pct_change(latest_val, prev_6) if prev_6 else 0
            cards.append({
                'community': community,
                'layout': layout,
                'latest_month': latest['month'],
                'latest_value': latest_val,
                'mom': mom,
                'qoq': qoq,
                'half': half,
                'trend': trend_text(mom),
                'signal': signal_class(mom),
            })
    cards.sort(key=lambda x: (x['community'], x['layout']))
    return cards


def build_rankings(trend_cards, key_name, title, limit=8, reverse=True):
    items = [x for x in trend_cards if abs(x[key_name]) > 0.01]
    items = sorted(items, key=lambda x: x[key_name], reverse=reverse)[:limit]
    if not items:
        return '<div class="card">目前沒有足夠變化可排行</div>'
    rows = []
    for idx, item in enumerate(items, 1):
        rows.append(
            f'<tr data-community="{esc(item["community"])}" data-layout="{esc(item["layout"])}">'
            f'<td>{idx}</td><td>{esc(item["community"])}</td><td>{esc(item["layout"])}</td><td>{item[key_name]:+.2f}%</td><td>{esc(item["latest_month"])}</td></tr>'
        )
    return (
        f'<section><h3>{esc(title)}</h3>'
        '<table><thead><tr><th>#</th><th>社區</th><th>房型</th><th>變化</th><th>最新月份</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></section>'
    )


def svg_line_chart(series_map, title, chart_id):
    width = 920
    height = 340
    margin = {'left': 56, 'right': 90, 'top': 24, 'bottom': 44}
    all_months = sorted({point['month'] for points in series_map.values() for point in points})
    all_vals = [calc_series_value(point) for points in series_map.values() for point in points if calc_series_value(point) > 0]
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

    colors = ['#1d4ed8', '#dc2626', '#059669', '#d97706', '#7c3aed', '#0f766e', '#be123c', '#4338ca', '#65a30d', '#c2410c']
    dashes = ['', '8 5', '4 4', '10 4 2 4', '2 4', '12 6', '6 3 2 3', '', '8 4 2 4', '3 3']

    grid = []
    for step in range(5):
        y_val = min_y + (max_y - min_y) * step / 4
        y = y_of(y_val)
        grid.append(f'<line x1="{margin["left"]}" y1="{y:.1f}" x2="{width-margin["right"]}" y2="{y:.1f}" stroke="#e5e7eb" />')
        grid.append(f'<text x="{margin["left"]-8}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="#6b7280">{y_val:.1f}</text>')

    x_labels = []
    label_step = 3 if len(all_months) > 18 else 2 if len(all_months) > 10 else 1
    for idx, month in enumerate(all_months):
        if idx % label_step != 0 and idx != len(all_months) - 1:
            continue
        x = x_of(idx)
        x_labels.append(f'<text x="{x:.1f}" y="{height-14}" text-anchor="middle" font-size="11" fill="#6b7280">{esc(month)}</text>')

    series_blocks = []
    legends = []
    for i, (label, points) in enumerate(series_map.items()):
        color = colors[i % len(colors)]
        dash = dashes[i % len(dashes)]
        month_to_point = {p['month']: p for p in points}
        coords = []
        dots = []
        plotted = []
        for idx, month in enumerate(all_months):
            point = month_to_point.get(month)
            if not point:
                continue
            value = calc_series_value(point)
            x = x_of(idx)
            y = y_of(value)
            coords.append(f'{x:.1f},{y:.1f}')
            plotted.append((x, y, point))
            point_fill = color if point.get('has_real') else '#ffffff'
            point_note = '含真實樣本' if point.get('has_real') else '僅 baseline'
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.6" fill="{point_fill}" stroke="{color}" stroke-width="2"><title>{esc(label)} {esc(month)}: 價格指標 {value:.2f} 萬/坪 (n={point["sample_count"]}, {point_note})</title></circle>')
        if coords:
            label_text = ''
            if plotted:
                lx, ly, _ = plotted[-1]
                label_text = f'<text x="{min(lx + 10, width - 4):.1f}" y="{max(ly + 4, 16):.1f}" font-size="12" font-weight="700" fill="{color}">{esc(label)}</text>'
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
            series_blocks.append(
                f'<g class="chart-series" data-series="{esc(label)}">'
                f'<polyline fill="none" stroke="{color}" stroke-width="3.5"{dash_attr} points="{" ".join(coords)}" />'
                f'{"".join(dots)}{label_text}</g>'
            )
            legends.append(
                f'<button type="button" class="legend-item is-active" data-chart="{esc(chart_id)}" data-series="{esc(label)}" aria-pressed="true">'
                f'<span class="legend-swatch" style="background:{color}; border:2px solid {color};"></span>'
                f'<span class="legend-name">{esc(label)}</span></button>'
            )

    return f'''
    <div class="card chart-card" data-chart-id="{esc(chart_id)}">
      <div class="chart-head">
        <div>
          <h3>{esc(title)}</h3>
          <p class="muted">顯示每月價格指標變化。實心點＝含真實樣本，空心點＝目前只有 baseline。</p>
        </div>
        <div class="legend legend-buttons">{"".join(legends)}</div>
      </div>
      <svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="{esc(title)}">
        {''.join(grid)}
        <line x1="{margin['left']}" y1="{height-margin['bottom']}" x2="{width-margin['right']}" y2="{height-margin['bottom']}" stroke="#9ca3af" />
        <line x1="{margin['left']}" y1="{margin['top']}" x2="{margin['left']}" y2="{height-margin['bottom']}" stroke="#9ca3af" />
        {''.join(series_blocks)}
        {''.join(x_labels)}
      </svg>
      <p class="muted mobile-hint">提示：可點上方 legend 開關線條。X 軸日期已做抽樣顯示，避免全部擠在一起。</p>
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
    by_series = defaultdict(list)
    for row in rows:
        if row.get('region'):
            by_region[row['region']].append(row)
        if row.get('community'):
            by_community[row['community']].append(row)
        layout = row.get('layout_type') or '未分類'
        by_layout[layout].append(row)
        if row.get('community'):
            by_series[(row['community'], layout, row.get('observed_month', ''))].append(row)

    communities = sorted(by_community)
    all_layouts = sorted({x.get('layout_type') or '未分類' for x in rows})

    series_export = []
    for (community, layout, month), items in sorted(by_series.items()):
        unit_prices = [x.get('unit_price', 0) for x in items]
        total_prices = [x.get('total_price', 0) for x in items]
        sources_list = sorted({x.get('source', '') for x in items if x.get('source')})
        has_real = any(x.get('source') != 'public-baseline' for x in items)
        has_baseline = any(x.get('source') == 'public-baseline' for x in items)
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
            'sources': sources_list,
            'has_real': has_real,
            'has_baseline': has_baseline
        })

    SERIES_CACHE_PATH.write_text(json.dumps(series_export, ensure_ascii=False, indent=2))

    trend_cards = build_trend_summary(series_export, communities, all_layouts)
    latest_month = max((x['latest_month'] for x in trend_cards), default='—')
    up_count = sum(1 for x in trend_cards if x['signal'] == 'up')
    down_count = sum(1 for x in trend_cards if x['signal'] == 'down')
    flat_count = sum(1 for x in trend_cards if x['signal'] == 'flat')

    summary_cards = [
        ('追蹤社區', str(len(communities))),
        ('房型數', str(len(all_layouts))),
        ('追蹤月份', str(len(sorted({x[2] for x in by_series.keys()})))),
        ('最新月份', latest_month),
        ('本月上升組合', str(up_count)),
        ('本月下降組合', str(down_count)),
        ('本月持平組合', str(flat_count)),
    ]
    summary_html = ''.join(
        f'<div class="card stat-card"><div class="eyebrow">{esc(label)}</div><h2>{esc(value)}</h2></div>'
        for label, value in summary_cards
    )

    trend_card_html = []
    for item in trend_cards:
        trend_card_html.append(f'''
        <div class="card trend-card {item['signal']}" data-community="{esc(item['community'])}" data-layout="{esc(item['layout'])}">
          <div class="eyebrow">{esc(item['community'])}｜{esc(item['layout'])}</div>
          <h3>{item['latest_month']}</h3>
          <p>最新價格指標：<strong>{item['latest_value']:.2f}</strong> 萬/坪</p>
          <p>月變化：<strong>{item['mom']:+.2f}%</strong></p>
          <p>3 個月變化：<strong>{item['qoq']:+.2f}%</strong></p>
          <p>6 個月變化：<strong>{item['half']:+.2f}%</strong></p>
          <p class="muted">短期趨勢：{esc(item['trend'])}</p>
        </div>
        ''')

    focus_chart_blocks = []
    watch_community_cards = []
    coverage_rows = []
    for item in watchlist.get('communities', []):
        name = item.get('name', '')
        nearby = item.get('nearby_communities', [])
        nearby_html = ''.join(chip(x) for x in nearby) or '<span class="muted">尚未補上附近社區</span>'
        watch_community_cards.append(f'''
        <div class="card priority-{esc(item.get('priority', '')).lower()}" data-community="{esc(name)}">
          <div class="eyebrow">觀察清單</div>
          <h3>{esc(name)}</h3>
          <p>區域：{esc(item.get('region', ''))}</p>
          <div class="nearby-block"><strong>附近社區：</strong><div class="chips">{nearby_html}</div></div>
        </div>
        ''')
        layouts_present = sorted({x['layout_type'] for x in series_export if x['community'] == name})
        coverage_rows.append(
            f'<tr data-community="{esc(name)}"><td>{esc(name)}</td><td>{esc(item.get("region", ""))}</td><td>{len(layouts_present)}</td><td>{", ".join(esc(x) for x in layouts_present) or "—"}</td></tr>'
        )
        if name == '摩納哥社區':
            focus_names = [name] + nearby
            default_layout = '2房' if '2房' in all_layouts else (all_layouts[0] if all_layouts else '未分類')
            series_map = {}
            for focus_name in focus_names:
                pts = [s for s in series_export if s['community'] == focus_name and s['layout_type'] == default_layout]
                if pts:
                    series_map[focus_name] = pts
            focus_chart_blocks.append(svg_line_chart(series_map, f'摩納哥周邊 {default_layout} 價格走勢', 'monaco-nearby'))

    rankings_html = (
        build_rankings(trend_cards, 'mom', '近 1 月上升排行', reverse=True) +
        build_rankings(trend_cards, 'qoq', '近 3 月上升排行', reverse=True) +
        build_rankings(trend_cards, 'half', '近 6 月上升排行', reverse=True)
    )

    community_options = ['<option value="">全部社區</option>'] + [f'<option value="{esc(c)}">{esc(c)}</option>' for c in communities]
    layout_options = ['<option value="">全部房型</option>'] + [f'<option value="{esc(l)}">{esc(l)}</option>' for l in all_layouts]

    html = f'''<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>淡水房市追蹤 Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 0; background: #f7f8fb; color: #1f2937; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 20px; }}
    .hero {{ background: white; border-radius: 16px; padding: 20px; box-shadow: 0 6px 18px rgba(0,0,0,.06); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-top: 16px; }}
    .card {{ background: white; border-radius: 14px; padding: 16px; box-shadow: 0 4px 14px rgba(0,0,0,.05); }}
    .stat-card h2 {{ margin: 8px 0 0; font-size: 28px; }}
    .priority-high {{ border: 2px solid #f59e0b; }}
    .chip {{ display: inline-block; padding: 6px 10px; border-radius: 999px; background: #eef2ff; font-size: 13px; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
    .nearby-block {{ margin-top: 12px; }}
    .eyebrow {{ font-size: 12px; color: #6366f1; font-weight: 700; letter-spacing: .04em; margin-bottom: 8px; }}
    .chart-head {{ display:flex; gap:12px; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; }}
    .legend {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
    .legend-item {{ display:inline-flex; align-items:center; gap:6px; font-size:13px; color:#374151; background:white; border:1px solid #d1d5db; border-radius:999px; padding:6px 10px; cursor:pointer; white-space:nowrap; }}
    .legend-item.is-muted {{ opacity:.45; }}
    .legend-swatch {{ width:12px; height:12px; border-radius:999px; display:inline-block; flex:0 0 auto; }}
    .chart {{ width:100%; height:auto; margin-top:12px; }}
    .chart-series.is-hidden {{ opacity:.12; }}
    .mobile-hint {{ margin-top:8px; font-size:13px; }}
    .trend-card.up {{ border-left: 5px solid #16a34a; }}
    .trend-card.down {{ border-left: 5px solid #dc2626; }}
    .trend-card.flat {{ border-left: 5px solid #6b7280; }}
    .controls {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-top:16px; }}
    .control label {{ display:block; font-size:13px; font-weight:600; margin-bottom:6px; color:#374151; }}
    .control select {{ width:100%; padding:10px 12px; border-radius:10px; border:1px solid #d1d5db; background:white; }}
    .tabbar {{ display:flex; gap:10px; overflow:auto; padding:10px 0 2px; margin-top:18px; scrollbar-width:thin; }}
    .tab-btn {{ border:0; background:#e5e7eb; color:#374151; padding:10px 14px; border-radius:999px; font-weight:600; cursor:pointer; white-space:nowrap; }}
    .tab-btn.active {{ background:#4f46e5; color:white; }}
    .tab-panel {{ display:none; margin-top:18px; }}
    .tab-panel.active {{ display:block; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 14px; overflow: hidden; margin-top: 16px; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #e5e7eb; font-size: 14px; vertical-align: top; }}
    th {{ background: #eef2ff; }}
    .muted {{ color: #6b7280; }}
    .hidden-row {{ display:none; }}
    @media (max-width: 720px) {{
      .wrap {{ padding: 14px; }}
      th, td {{ font-size: 13px; padding: 8px; }}
      .chart-head {{ flex-direction:column; }}
      .legend {{ display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); width:100%; }}
      .legend-item {{ justify-content:flex-start; width:100%; }}
      .mobile-hint {{ font-size:12px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>淡水房市追蹤 Dashboard</h1>
      <p class="muted">重點看每月價格變化與社區相對位置，不展示過多逐筆細節。</p>
      <p>目前觀察區域：{', '.join(esc(x) for x in watchlist.get('regions', []))}</p>
      <p>房型分類：{', '.join(esc(x) for x in watchlist.get('layout_types', []))}</p>
      <div class="controls">
        <div class="control">
          <label for="communityFilter">篩選社區</label>
          <select id="communityFilter">{''.join(community_options)}</select>
        </div>
        <div class="control">
          <label for="layoutFilter">篩選房型</label>
          <select id="layoutFilter">{''.join(layout_options)}</select>
        </div>
      </div>
      <div class="tabbar" role="tablist">
        <button class="tab-btn active" data-tab="overview" role="tab">總覽</button>
        <button class="tab-btn" data-tab="trends" role="tab">走勢</button>
        <button class="tab-btn" data-tab="ranking" role="tab">排行</button>
        <button class="tab-btn" data-tab="coverage" role="tab">追蹤覆蓋</button>
      </div>
    </section>

    <section class="tab-panel active" data-panel="overview">
      <section>
        <h2>總覽</h2>
        <div class="grid">{summary_html}</div>
      </section>
      <section>
        <h2>月度價格變化摘要</h2>
        <div class="grid">{''.join(trend_card_html) or '<div class="card">目前尚無足夠資料可計算月度變化</div>'}</div>
      </section>
    </section>

    <section class="tab-panel" data-panel="trends">
      {''.join(focus_chart_blocks) or '<div class="card">目前沒有可顯示的趨勢圖</div>'}
      <section>
        <h2>觀察清單</h2>
        <div class="grid">{''.join(watch_community_cards) or '<div class="card">目前尚未設定</div>'}</div>
      </section>
    </section>

    <section class="tab-panel" data-panel="ranking">
      {rankings_html}
    </section>

    <section class="tab-panel" data-panel="coverage">
      <section>
        <h2>追蹤覆蓋狀態</h2>
        <table id="coverage-table">
          <thead><tr><th>社區</th><th>區域</th><th>已覆蓋房型數</th><th>房型</th></tr></thead>
          <tbody>{''.join(coverage_rows) or '<tr><td colspan="4">尚無覆蓋資料</td></tr>'}</tbody>
        </table>
      </section>
      <section class="card">
        <h2>資料說明</h2>
        <ul>
          <li>這個 dashboard 目前以「社區 × 房型 × 月份」的價格時間序列為主。</li>
          <li>前台刻意不展示逐筆 raw data，也不強調平均數 / 中位數的統計字樣，避免在 real data 稀少時造成過度解讀。</li>
          <li>現在主要目的，是看每月變化方向、相對位置、以及哪些社區已納入長期追蹤。</li>
        </ul>
      </section>
    </section>
  </div>
  <script>
    function applyFilters() {{
      const community = document.getElementById('communityFilter').value;
      const layout = document.getElementById('layoutFilter').value;
      document.querySelectorAll('[data-community], [data-layout]').forEach((row) => {{
        const rowCommunity = row.dataset.community || '';
        const rowLayout = row.dataset.layout || '';
        const okCommunity = !community || rowCommunity === community;
        const okLayout = !layout || rowLayout === layout;
        row.classList.toggle('hidden-row', !(okCommunity && okLayout));
      }});
    }}

    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');
    const savedTab = localStorage.getItem('housingTrackerTab') || 'overview';

    function activateTab(tab) {{
      tabButtons.forEach((btn) => btn.classList.toggle('active', btn.dataset.tab === tab));
      tabPanels.forEach((panel) => panel.classList.toggle('active', panel.dataset.panel === tab));
      localStorage.setItem('housingTrackerTab', tab);
    }}

    function setupLegendToggles() {{
      document.querySelectorAll('.legend-item[data-chart]').forEach((btn) => {{
        btn.addEventListener('click', () => {{
          const chartId = btn.dataset.chart;
          const seriesName = btn.dataset.series;
          const target = document.querySelector(`[data-chart-id="${{chartId}}"] .chart-series[data-series="${{seriesName}}"]`);
          if (!target) return;
          const hidden = target.classList.toggle('is-hidden');
          btn.classList.toggle('is-muted', hidden);
          btn.setAttribute('aria-pressed', hidden ? 'false' : 'true');
        }});
      }});
    }}

    tabButtons.forEach((btn) => {{
      btn.addEventListener('click', () => activateTab(btn.dataset.tab));
    }});
    document.getElementById('communityFilter').addEventListener('change', applyFilters);
    document.getElementById('layoutFilter').addEventListener('change', applyFilters);

    activateTab(savedTab);
    applyFilters();
    setupLegendToggles();
  </script>
</body>
</html>
'''
    OUT_PATH.write_text(html)
    print(OUT_PATH)


if __name__ == '__main__':
    main()
