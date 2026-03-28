from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from pathlib import Path
import json
from collections import Counter

ROOT = Path('/home/gigo/.openclaw/projects/tamsui-housing-tracker')
OUT = ROOT / 'docs' / 'tamsui-housing-progress-report.pdf'

watch = json.loads((ROOT / 'data' / 'watchlist.json').read_text())
obs = json.loads((ROOT / 'data' / 'observations.json').read_text())
series = json.loads((ROOT / 'data' / 'series_cache.json').read_text())

real_obs = [o for o in obs if o.get('source_type') != 'baseline']
months = sorted({o.get('observed_month') for o in obs if o.get('observed_month')})
real_months = sorted({o.get('observed_month') for o in real_obs if o.get('observed_month')})
real_comms = sorted({o.get('community') for o in real_obs if o.get('community')})
series_real = [s for s in series if s.get('has_real')]
series_pairs = sorted({(s['community'], s['layout_type']) for s in series})
real_count_by_comm = Counter(o['community'] for o in real_obs)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleCenter', parent=styles['Title'], alignment=TA_CENTER, fontName='Helvetica-Bold'))
styles.add(ParagraphStyle(name='Section', parent=styles['Heading1'], fontName='Helvetica-Bold', textColor=colors.HexColor('#1f3a8a'), spaceAfter=8))
styles.add(ParagraphStyle(name='BodyCJKish', parent=styles['BodyText'], leading=18, spaceAfter=6))
styles.add(ParagraphStyle(name='Small', parent=styles['BodyText'], fontSize=9, leading=12, textColor=colors.grey))

story = []
story.append(Spacer(1, 18*mm))
story.append(Paragraph('淡水房價搜尋／追蹤專案進度報告', styles['TitleCenter']))
story.append(Spacer(1, 6*mm))
story.append(Paragraph('專案：Tamsui Housing Tracker', styles['BodyCJKish']))
story.append(Paragraph('報告時間：2026-03-28', styles['BodyCJKish']))
story.append(Paragraph('定位：以「月度 baseline-first」方式，先建立可持續追蹤的社區 × 房型價格序列，再逐步增加真實樣本與自動化。', styles['BodyCJKish']))

story.append(Spacer(1, 6*mm))
story.append(Paragraph('一頁結論', styles['Section']))
summary_items = [
    '專案 MVP 已成形：資料結構、更新腳本、月度序列、靜態 dashboard 都已經存在。',
    f'目前累積原始 observation 共 {len(obs)} 筆，其中 baseline {len(obs)-len(real_obs)} 筆、真實樣本 {len(real_obs)} 筆。',
    f'月度追蹤涵蓋 {months[0]} 到 {months[-1]}，共 {len(months)} 個月份。',
    f'已形成 {len(series_pairs)} 組「社區 × 房型」月度序列，聚合後月序列共 {len(series)} 筆。',
    '核心追蹤對象已聚焦在摩納哥社區及其周邊 8 個鄰近社區，符合目前看屋/比較情境。',
    '現階段最大瓶頸不是程式，而是「真實樣本密度仍偏低」，因此現在比較像有骨架、有 dashboard、可持續累積，但還沒到高可信自動估價。',
]
story.append(ListFlowable([ListItem(Paragraph(x, styles['BodyCJKish'])) for x in summary_items], bulletType='bullet'))

story.append(PageBreak())
story.append(Paragraph('目前完成了什麼', styles['Section']))
completed = [
    '已建立專案 repo 與基本結構（README、data、scripts、docs）。',
    '已定義 watchlist：區域、重點社區、房型分類、摩納哥周邊社區名單。',
    '已建立 observation schema，可記錄總價、單價、坪數、屋齡、車位、來源、月份等欄位。',
    '已完成 baseline series builder：能把社區 × 房型資料整理成每月序列。',
    '已完成 dashboard builder：輸出靜態 HTML dashboard。',
    '已完成 canonical update pipeline（update_all.py），代表後續手動更新流程已經有主入口。',
]
story.append(ListFlowable([ListItem(Paragraph(x, styles['BodyCJKish'])) for x in completed], bulletType='bullet'))

story.append(Spacer(1, 4*mm))
story.append(Paragraph('目前資料規模', styles['Section']))
metrics = [
    ['指標', '數值'],
    ['觀察區域數', str(len(watch['regions']))],
    ['核心 watch 社區數', str(len([c for c in watch['communities'] if isinstance(c, dict)]))],
    ['摩納哥周邊社區數', str(len(watch['communities'][0]['nearby_communities']))],
    ['房型分類數', str(len(watch['layout_types']))],
    ['原始 observation', str(len(obs))],
    ['真實樣本 observation', str(len(real_obs))],
    ['baseline observation', str(len(obs)-len(real_obs))],
    ['聚合月序列筆數', str(len(series))],
    ['有真實樣本的月序列筆數', str(len(series_real))],
    ['社區 × 房型組合數', str(len(series_pairs))],
    ['涵蓋月份', f'{months[0]} ~ {months[-1]}'],
]
t = Table(metrics, colWidths=[60*mm, 90*mm])
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dbeafe')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#111827')),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
]))
story.append(t)

story.append(PageBreak())
story.append(Paragraph('目前資料內容的判讀', styles['Section']))
insights = [
    '現在的資料主體仍是 baseline-first：也就是先確保每個社區 × 房型都有月度參考點，讓趨勢圖能先跑起來。',
    '真實樣本已經開始混入部分月份，代表架構已能支援 baseline 與實際公開樣本共存。',
    f'目前有真實樣本的社區包括：{", ".join(real_comms[:10])}。',
    '其中，清淞、荷雅名人館、荷雅時尚館、尚海、托斯卡尼麥迪奇名家、高第的真實樣本相對較多。',
    '摩納哥社區本身已經進入序列，但真實樣本量仍偏少，所以現在更適合拿來看「位置與方向」，還不適合做太精細的價格判斷。',
]
story.append(ListFlowable([ListItem(Paragraph(x, styles['BodyCJKish'])) for x in insights], bulletType='bullet'))

rank_rows = [['社區', '真實樣本筆數']]
for comm, cnt in real_count_by_comm.most_common(8):
    rank_rows.append([comm, str(cnt)])
rt = Table(rank_rows, colWidths=[90*mm, 40*mm])
rt.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dbeafe')),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
]))
story.append(Spacer(1, 4*mm))
story.append(rt)

story.append(PageBreak())
story.append(Paragraph('我認為目前進度在哪一階段', styles['Section']))
stage_items = [
    '如果用產品階段來看，現在大概是：<b>MVP 已完成、資料擴充期剛開始</b>。',
    '不是只有概念，因為資料模型、腳本、dashboard 都能運作。',
    '但也還不是成熟產品，因為資料來源與真實樣本覆蓋率還不足，還需要持續補樣本。',
    '這個階段最有價值的不是再重寫前端，而是持續提高真實 observation 的密度與更新節奏。',
]
story.append(ListFlowable([ListItem(Paragraph(x, styles['BodyCJKish'])) for x in stage_items], bulletType='bullet'))

story.append(Spacer(1, 4*mm))
story.append(Paragraph('目前風險／不足', styles['Section']))
risk_items = [
    '真實樣本占比低，baseline 仍然是主體，因此序列的穩定性高，但靈敏度不足。',
    'watchlist 結構目前只有 1 個核心 watch community 物件（摩納哥社區），其他多數社區比較像透過 nearby cluster 進來。',
    '部分資料仍明顯帶有示例/測試痕跡（例如 示例社區），之後應整理掉，避免污染正式報表。',
    '目前偏向單機 JSON 流程，優點是簡單，但若未來資料量再大，可能要考慮 SQLite 或更正式的資料層。',
]
story.append(ListFlowable([ListItem(Paragraph(x, styles['BodyCJKish'])) for x in risk_items], bulletType='bullet'))

story.append(PageBreak())
story.append(Paragraph('下一步建議（務實版）', styles['Section']))
next_items = [
    '優先持續補「摩納哥社區 + 周邊 8 社區」的真實樣本，尤其是 2房 / 3房。',
    '整理掉示例資料，讓正式 dashboard 更乾淨。',
    '加一份「真實樣本覆蓋率」統計，直接看每個社區 × 房型有多少月份只有 baseline。',
    '如果你要開始實際看屋，可把看屋路線上的新社區加進 nearby 清單。',
    '等真實樣本密度夠了，再來做告警、排名、異常波動提示，才比較值得。',
]
story.append(ListFlowable([ListItem(Paragraph(x, styles['BodyCJKish'])) for x in next_items], bulletType='bullet'))

story.append(Spacer(1, 6*mm))
story.append(Paragraph('一句話總結', styles['Section']))
story.append(Paragraph('這個專案現在已經不是「想法」，而是有資料骨架、有更新流程、有 dashboard 的可運作原型；下一階段的重點不是重做，而是把真實樣本補厚，讓它從可看趨勢，進一步變成可輔助判斷。', styles['BodyCJKish']))

story.append(Spacer(1, 8*mm))
story.append(Paragraph('附註：本報告依據專案內 README、watchlist、observations、series_cache 與 docs dashboard 整理。', styles['Small']))

doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=14*mm, bottomMargin=14*mm)
doc.build(story)
print(OUT)
