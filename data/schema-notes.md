# Schema Notes

Each observation row currently supports:

- `observed_at`: date string
- `type`: seed / listing / transaction / manual-note
- `region`: area name in Tamsui
- `community`: community/building name
- `layout_type`: 套房 / 1房 / 2房 / 3房 / 4房以上
- `rooms`: optional numeric room count
- `source`: manual / 591 / realprice / etc
- `total_price`: total price in 萬
- `unit_price`: price per ping in 萬/坪
- `size_ping`: indoor/building size in 坪
- `building_age`: years
- `parking`: true/false
- `note`: free text

Watchlist community object can also include:

- `name`: focal community name
- `region`: area name
- `priority`: high / medium / low
- `notes`: why it matters
- `nearby_communities`: nearby comparable communities for local comparison

Why this matters:

- 套房、兩房、三房的單價常常不在同一個比較基準
- 同時，社區也不能只孤立看，附近可比社區常常更有參考價值
- MVP 起步時，先做簡單房型分組 + 周邊社區清單，比直接混合平均更合理
