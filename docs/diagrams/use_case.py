"""Генерация диаграммы вариантов использования (UML Use Case) в SVG."""
from pathlib import Path

FONT = "'Segoe UI', 'DejaVu Sans', Arial, sans-serif"
W, H = 1500, 1000
EW, EH = 300, 58  # размер овалов


def actor(x, y, name):
    """Человечек: (x, y) — центр головы."""
    return f'''
<g stroke="#1f2937" stroke-width="2.2" fill="none">
  <circle cx="{x}" cy="{y}" r="16" fill="#ffffff"/>
  <line x1="{x}" y1="{y + 16}" x2="{x}" y2="{y + 62}"/>
  <line x1="{x - 28}" y1="{y + 32}" x2="{x + 28}" y2="{y + 32}"/>
  <line x1="{x}" y1="{y + 62}" x2="{x - 24}" y2="{y + 98}"/>
  <line x1="{x}" y1="{y + 62}" x2="{x + 24}" y2="{y + 98}"/>
</g>
<text x="{x}" y="{y + 124}" text-anchor="middle" font-size="18" font-weight="700">{name}</text>'''


def usecase(cx, cy, text, fill='#dae8fc', stroke='#6c8ebf'):
    lines = text.split('|')
    start = cy - (len(lines) - 1) * 10 + 6
    t = ''.join(f'<tspan x="{cx}" y="{start + i * 20}">{line}</tspan>' for i, line in enumerate(lines))
    return (f'<ellipse cx="{cx}" cy="{cy}" rx="{EW / 2}" ry="{EH / 2}" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>'
            f'<text text-anchor="middle" font-size="16">{t}</text>')


def line(x1, y1, x2, y2, dash=False, arrow=None):
    extra = ' stroke-dasharray="7 5"' if dash else ''
    marker = f' marker-end="url(#{arrow})"' if arrow else ''
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#1f2937" stroke-width="1.8"{extra}{marker}/>'


def build():
    p = []
    # Граница системы
    p.append('<rect x="330" y="40" width="880" height="880" rx="14" fill="#f9fafb" stroke="#374151" stroke-width="2"/>')
    p.append('<text x="770" y="78" text-anchor="middle" font-size="21" font-weight="700">'
             'Веб-приложение «SubTracker»</text>')

    col_a, col_b, col_c = 540, 880, 1020
    left_a = col_a - EW / 2

    # --- Гость ---
    guest = (140, 140)
    guest_cases = [(150, 'Регистрация'), (230, 'Вход в систему')]
    p.append(actor(*guest, 'Гость'))
    for y, text in guest_cases:
        p.append(line(guest[0] + 30, guest[1] + 40, left_a, y))
        p.append(usecase(col_a, y, text, '#e1d5e7', '#9673a6'))

    # --- Пользователь ---
    user = (140, 520)
    user_cases = [
        (330, 'Управление подписками|(CRUD)'),
        (410, 'Изменение статуса|подписки'),
        (490, 'Отметка об оплате'),
        (570, 'Ведение истории|расходов'),
        (650, 'Просмотр календаря|списаний'),
        (730, 'Анализ расходов'),
        (810, 'Просмотр уведомлений'),
        (880, 'Настройка профиля|и бюджета'),
    ]
    p.append(actor(*user, 'Пользователь'))
    for y, text in user_cases:
        p.append(line(user[0] + 30, user[1] + 40, left_a, y))
        p.append(usecase(col_a, y, text))

    # --- Расширения и включения (колонка B) ---
    # «Выгрузка отчёта» расширяет «Анализ расходов»
    p.append(usecase(col_b + 60, 690, 'Выгрузка отчёта|в CSV / Excel', '#fff2cc', '#d6b656'))
    p.append(line(col_b + 60 - EW / 2 + 8, 690, col_a + EW / 2 - 4, 722, dash=True, arrow='open'))
    p.append('<text x="745" y="688" text-anchor="middle" font-size="14" fill="#374151">«extend»</text>')
    # «Анализ расходов» включает «Пересчёт по курсу валют»
    p.append(usecase(col_b + 60, 790, 'Пересчёт сумм|по курсу валют', '#fff2cc', '#d6b656'))
    p.append(line(col_a + EW / 2 - 4, 738, col_b + 60 - EW / 2 + 8, 786, dash=True, arrow='open'))
    p.append('<text x="690" y="800" text-anchor="middle" font-size="14" fill="#374151">«include»</text>')
    # «Отметка об оплате» включает «Расчёт даты следующего списания»
    p.append(usecase(col_b + 60, 490, 'Расчёт даты|следующего списания', '#fff2cc', '#d6b656'))
    p.append(line(col_a + EW / 2, 490, col_b + 60 - EW / 2 - 2, 490, dash=True, arrow='open'))
    p.append('<text x="760" y="478" text-anchor="middle" font-size="14" fill="#374151">«include»</text>')

    # --- Администратор ---
    admin = (1360, 300)
    admin_cases = [
        (150, 'Управление|пользователями и ролями'),
        (240, 'Управление категориями'),
        (330, 'Управление валютами|и курсами'),
        (420, 'Просмотр статистики|системы'),
    ]
    p.append(actor(*admin, 'Администратор'))
    right_c = col_c + 30 + EW / 2
    for y, text in admin_cases:
        p.append(line(admin[0] - 30, admin[1] + 40, right_c, y))
        p.append(usecase(col_c + 30, y, text, '#d5e8d4', '#82b366'))

    # --- Обобщение: Администратор —|> Пользователь (обходим систему снизу) ---
    p.append(f'<path d="M{admin[0]} {admin[1] + 130} V960 H{user[0]} V{user[1] + 134}" fill="none" '
             f'stroke="#1f2937" stroke-width="1.8" marker-end="url(#triangle)"/>')
    p.append(f'<text x="770" y="985" text-anchor="middle" font-size="14" fill="#374151">'
             f'администратор наследует возможности пользователя</text>')

    defs = '''<defs>
  <marker id="open" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="12" markerHeight="12" orient="auto-start-reverse">
    <path d="M1 1 L11 6 L1 11" fill="none" stroke="#1f2937" stroke-width="1.6"/></marker>
  <marker id="triangle" viewBox="0 0 16 16" refX="15" refY="8" markerWidth="18" markerHeight="18" orient="auto-start-reverse">
    <path d="M1 1 L15 8 L1 15 Z" fill="#ffffff" stroke="#1f2937" stroke-width="1.5"/></marker>
</defs>'''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'font-family="{FONT}">{defs}<rect width="100%" height="100%" fill="#fff"/>' + '\n'.join(p) + '</svg>')


if __name__ == '__main__':
    out = Path(__file__).parent / 'use_case_diagram.svg'
    out.write_text(build(), encoding='utf-8')
