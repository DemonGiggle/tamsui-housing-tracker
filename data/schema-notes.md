# Schema Notes

Each observation row currently supports:

- `observed_at`: date string
- `type`: seed / listing / transaction / manual-note
- `region`: area name in Tamsui
- `community`: community/building name
- `source`: manual / 591 / realprice / etc
- `total_price`: total price in 萬
- `unit_price`: price per ping in 萬/坪
- `size_ping`: indoor/building size in 坪
- `building_age`: years
- `parking`: true/false
- `note`: free text

This is intentionally small for MVP.
