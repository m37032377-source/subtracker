"""Генерация ER-диаграммы (нотация Crow's Foot) в SVG в стиле draw.io.

Связи проводятся ортогональными линиями от строки PK к строке FK,
раскладка подобрана так, чтобы линии не пересекались.
"""
from pathlib import Path

ROW = 30
HEAD = 38
FONT = "'Segoe UI', 'DejaVu Sans', Arial, sans-serif"

TABLES = {
    'users': dict(x=70, y=120, w=330, color='#dae8fc', stroke='#6c8ebf', rows=[
        ('PK', 'id', 'BIGINT'), ('', 'email', 'VARCHAR(254)'), ('', 'password', 'VARCHAR(128)'),
        ('', 'first_name', 'VARCHAR(150)'), ('', 'last_name', 'VARCHAR(150)'),
        ('', 'role', 'VARCHAR(10)'), ('FK', 'default_currency_id', 'BIGINT'),
        ('', 'monthly_budget', 'DECIMAL(10,2)'), ('', 'is_active', 'BOOLEAN'),
        ('', 'date_joined', 'DATETIME')]),
    'currencies': dict(x=70, y=520, w=330, color='#d5e8d4', stroke='#82b366', rows=[
        ('PK', 'id', 'BIGINT'), ('', 'code', 'VARCHAR(3)'), ('', 'name', 'VARCHAR(50)'),
        ('', 'symbol', 'VARCHAR(5)'), ('', 'rate_to_rub', 'DECIMAL(12,4)'),
        ('', 'updated_at', 'DATETIME')]),
    'subscriptions': dict(x=570, y=90, w=340, color='#ffe6cc', stroke='#d79b00', rows=[
        ('PK', 'id', 'BIGINT'), ('FK', 'user_id', 'BIGINT'), ('FK', 'currency_id', 'BIGINT'),
        ('FK', 'category_id', 'BIGINT'), ('', 'name', 'VARCHAR(100)'), ('', 'price', 'DECIMAL(10,2)'),
        ('', 'billing_period', 'VARCHAR(10)'), ('', 'status', 'VARCHAR(10)'),
        ('', 'start_date', 'DATE'), ('', 'next_payment_date', 'DATE'), ('', 'trial_end_date', 'DATE'),
        ('', 'remind_days_before', 'SMALLINT'), ('', 'website', 'VARCHAR(200)'),
        ('', 'notes', 'TEXT'), ('', 'created_at', 'DATETIME'), ('', 'updated_at', 'DATETIME')]),
    'categories': dict(x=570, y=660, w=340, color='#d5e8d4', stroke='#82b366', rows=[
        ('PK', 'id', 'BIGINT'), ('', 'name', 'VARCHAR(60)'), ('', 'description', 'VARCHAR(255)'),
        ('', 'color', 'VARCHAR(7)'), ('', 'icon', 'VARCHAR(40)')]),
    'notifications': dict(x=1100, y=90, w=330, color='#e1d5e7', stroke='#9673a6', rows=[
        ('PK', 'id', 'BIGINT'), ('FK', 'subscription_id', 'BIGINT'), ('FK', 'user_id', 'BIGINT'),
        ('', 'notification_type', 'VARCHAR(12)'), ('', 'title', 'VARCHAR(150)'),
        ('', 'message', 'TEXT'), ('', 'event_date', 'DATE'), ('', 'is_read', 'BOOLEAN'),
        ('', 'created_at', 'DATETIME')]),
    'payments': dict(x=1100, y=450, w=330, color='#f8cecc', stroke='#b85450', rows=[
        ('PK', 'id', 'BIGINT'), ('FK', 'subscription_id', 'BIGINT'), ('FK', 'currency_id', 'BIGINT'),
        ('', 'amount', 'DECIMAL(10,2)'), ('', 'amount_rub', 'DECIMAL(12,2)'), ('', 'paid_at', 'DATE'),
        ('', 'status', 'VARCHAR(10)'), ('', 'comment', 'VARCHAR(255)'), ('', 'created_at', 'DATETIME')]),
}


def row_y(table, field):
    t = TABLES[table]
    index = [r[1] for r in t['rows']].index(field)
    return t['y'] + HEAD + ROW * index + ROW / 2


def left(table):
    return TABLES[table]['x']


def right(table):
    t = TABLES[table]
    return t['x'] + t['w']


def table_svg(name, t):
    x, y, w = t['x'], t['y'], t['w']
    h = HEAD + ROW * len(t['rows'])
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#ffffff" stroke="{t["stroke"]}" stroke-width="1.5"/>',
        f'<path d="M{x} {y + HEAD} V{y + 6} Q{x} {y} {x + 6} {y} H{x + w - 6} Q{x + w} {y} {x + w} {y + 6} V{y + HEAD} Z" '
        f'fill="{t["color"]}" stroke="{t["stroke"]}" stroke-width="1.5"/>',
        f'<text x="{x + w / 2}" y="{y + 25}" text-anchor="middle" font-weight="700" font-size="17">{name}</text>',
        f'<line x1="{x + 44}" y1="{y + HEAD}" x2="{x + 44}" y2="{y + h}" stroke="{t["stroke"]}" stroke-width="1"/>',
    ]
    for i, (key, field, ftype) in enumerate(t['rows']):
        ry = y + HEAD + ROW * i
        if i:
            out.append(f'<line x1="{x}" y1="{ry}" x2="{x + w}" y2="{ry}" stroke="#e5e7eb" stroke-width="1"/>')
        weight = '700' if key == 'PK' else '400'
        deco = ' text-decoration="underline"' if key == 'PK' else ''
        if key:
            out.append(f'<text x="{x + 22}" y="{ry + 20}" text-anchor="middle" font-size="13" font-weight="700" '
                       f'fill="{"#b45309" if key == "PK" else "#1d4ed8"}">{key}</text>')
        out.append(f'<text x="{x + 54}" y="{ry + 20}" font-size="14" font-weight="{weight}"{deco}>{field}</text>')
        out.append(f'<text x="{x + w - 10}" y="{ry + 20}" text-anchor="end" font-size="12" fill="#6b7280">{ftype}</text>')
    return '\n'.join(out)


def marker_one(x, y, d, optional=False):
    """Конец связи со стороны PK: «||» (ровно один) или «O|» (ноль или один).
    d = направление от таблицы наружу (+1 вправо, -1 влево)."""
    parts = [f'<line x1="{x + d * 10}" y1="{y - 8}" x2="{x + d * 10}" y2="{y + 8}" stroke="#374151" stroke-width="1.6"/>']
    if optional:
        parts.append(f'<circle cx="{x + d * 22}" cy="{y}" r="5" fill="#fff" stroke="#374151" stroke-width="1.6"/>')
    else:
        parts.append(f'<line x1="{x + d * 16}" y1="{y - 8}" x2="{x + d * 16}" y2="{y + 8}" stroke="#374151" stroke-width="1.6"/>')
    return '\n'.join(parts)


def marker_many(x, y, d, optional=True):
    """Конец связи со стороны FK: «O<» (ноль или много) или «|<» (один или много).
    d = направление от таблицы наружу."""
    parts = [
        f'<line x1="{x + d * 16}" y1="{y}" x2="{x}" y2="{y - 9}" stroke="#374151" stroke-width="1.6"/>',
        f'<line x1="{x + d * 16}" y1="{y}" x2="{x}" y2="{y + 9}" stroke="#374151" stroke-width="1.6"/>',
    ]
    if optional:
        parts.append(f'<circle cx="{x + d * 24}" cy="{y}" r="5" fill="#fff" stroke="#374151" stroke-width="1.6"/>')
    else:
        parts.append(f'<line x1="{x + d * 22}" y1="{y - 8}" x2="{x + d * 22}" y2="{y + 8}" stroke="#374151" stroke-width="1.6"/>')
    return '\n'.join(parts)


def path(points, color='#374151', dash=False):
    d = 'M' + ' L'.join(f'{x} {y}' for x, y in points)
    extra = ' stroke-dasharray="6 4"' if dash else ''
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6"{extra}/>'


def label(x, y, text, anchor='middle'):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="12" fill="#4b5563" '
            f'font-style="italic">{text}</text>')


def build():
    parts = []
    # --- Связи ---
    # users.id -> subscriptions.user_id (1 : 0..*)
    y1 = row_y('users', 'id')
    parts.append(path([(right('users'), y1), (left('subscriptions'), row_y('subscriptions', 'user_id'))]))
    parts += [marker_one(right('users'), y1, +1), marker_many(left('subscriptions'), y1, -1)]
    parts.append(label(515, y1 - 8, 'владеет'))

    # users.id -> notifications.user_id: через верх диаграммы
    top = 50
    ny = row_y('notifications', 'user_id')
    parts.append(path([(right('users'), y1), (460, y1), (460, top), (1470, top), (1470, ny), (right('notifications'), ny)]))
    parts.append(marker_many(right('notifications'), ny, +1))
    parts.append(label(960, top - 8, 'получает уведомления'))

    # currencies.id -> users.default_currency_id (0..1 : 0..*) — по левому краю
    cy = row_y('currencies', 'id')
    uy = row_y('users', 'default_currency_id')
    parts.append(path([(left('currencies'), cy), (20, cy), (20, uy), (left('users'), uy)]))
    parts += [marker_one(left('currencies'), cy, -1, optional=True), marker_many(left('users'), uy, -1)]

    # currencies.id -> subscriptions.currency_id
    sy = row_y('subscriptions', 'currency_id')
    parts.append(path([(right('currencies'), cy), (500, cy), (500, sy), (left('subscriptions'), sy)]))
    parts += [marker_one(right('currencies'), cy, +1), marker_many(left('subscriptions'), sy, -1)]

    # currencies.id -> payments.currency_id — по нижнему краю
    bottom = 900
    py2 = row_y('payments', 'currency_id')
    parts.append(path([(20, cy), (20, bottom), (1450, bottom), (1450, py2), (right('payments'), py2)]))
    parts.append(marker_many(right('payments'), py2, +1))
    parts.append(label(760, bottom - 8, 'валюта платежа'))

    # categories.id -> subscriptions.category_id
    ky = row_y('categories', 'id')
    sy3 = row_y('subscriptions', 'category_id')
    parts.append(path([(left('categories'), ky), (530, ky), (530, sy3), (left('subscriptions'), sy3)]))
    parts += [marker_one(left('categories'), ky, -1), marker_many(left('subscriptions'), sy3, -1)]

    # subscriptions.id -> payments.subscription_id и notifications.subscription_id
    s0 = row_y('subscriptions', 'id')
    n1 = row_y('notifications', 'subscription_id')
    p1 = row_y('payments', 'subscription_id')
    parts.append(path([(right('subscriptions'), s0), (990, s0), (990, n1), (left('notifications'), n1)]))
    parts.append(path([(990, s0), (990, p1), (left('payments'), p1)]))
    parts.append(marker_one(right('subscriptions'), s0, +1))
    parts.append(marker_many(left('notifications'), n1, -1))
    parts.append(marker_many(left('payments'), p1, -1))
    parts.append(label(1045, p1 - 8, 'история'))

    for name, t in TABLES.items():
        parts.append(table_svg(name, t))

    width, height = 1500, 930
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="{FONT}">\n'
           f'<rect width="100%" height="100%" fill="#ffffff"/>\n' + '\n'.join(parts) + '\n</svg>')
    return svg


if __name__ == '__main__':
    out = Path(__file__).parent / 'er_diagram.svg'
    out.write_text(build(), encoding='utf-8')
    print(out)
