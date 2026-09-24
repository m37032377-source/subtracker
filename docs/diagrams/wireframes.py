"""Генерация wireframe-макетов основных страниц (чёрно-серая схема без стилей)."""
from pathlib import Path

FONT = "'Segoe UI', 'DejaVu Sans', Arial, sans-serif"
W, H = 1200, 780
INK, MID, LIGHT, FILL = '#374151', '#9ca3af', '#e5e7eb', '#f3f4f6'


def rect(x, y, w, h, fill='#ffffff', stroke=INK, rx=6, dash=False, sw=1.6):
    d = ' stroke-dasharray="6 4"' if dash else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def text(x, y, s, size=16, weight=400, anchor='start', color=INK):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{color}">{s}</text>'


def bar(x, y, w, h=10):
    """Серая полоса — условное обозначение текста."""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{LIGHT}"/>'


def image_box(x, y, w, h, label=''):
    out = [rect(x, y, w, h, FILL, MID, 4),
           f'<line x1="{x}" y1="{y}" x2="{x + w}" y2="{y + h}" stroke="{MID}"/>',
           f'<line x1="{x + w}" y1="{y}" x2="{x}" y2="{y + h}" stroke="{MID}"/>']
    if label:
        out.append(f'<rect x="{x + w / 2 - 80}" y="{y + h / 2 - 16}" width="160" height="30" fill="{FILL}"/>')
        out.append(text(x + w / 2, y + h / 2 + 5, label, 15, 600, 'middle', '#4b5563'))
    return '\n'.join(out)


def button(x, y, w, label, primary=True):
    fill = '#4b5563' if primary else '#ffffff'
    color = '#ffffff' if primary else INK
    return rect(x, y, w, 36, fill, INK, 6) + text(x + w / 2, y + 23, label, 14, 600, 'middle', color)


def field(x, y, w, label, placeholder=''):
    return (text(x, y, label, 14, 600) + rect(x, y + 8, w, 36, '#ffffff', MID, 5)
            + (text(x + 10, y + 32, placeholder, 13, 400, 'start', MID) if placeholder else ''))


def frame(title, url, body, active):
    """Окно браузера + боковое меню приложения."""
    menu = ['Главная', 'Подписки', 'Календарь', 'История расходов', 'Аналитика', 'Уведомления']
    p = [rect(10, 10, W - 20, H - 20, '#ffffff', INK, 10, sw=2),
         f'<line x1="10" y1="50" x2="{W - 10}" y2="50" stroke="{INK}" stroke-width="2"/>',
         '<circle cx="34" cy="30" r="6" fill="none" stroke="#6b7280"/><circle cx="54" cy="30" r="6" fill="none" stroke="#6b7280"/>'
         '<circle cx="74" cy="30" r="6" fill="none" stroke="#6b7280"/>',
         rect(100, 19, 600, 22, FILL, MID, 11), text(115, 35, url, 13, 400, 'start', '#6b7280'),
         rect(10, 50, 220, H - 60, FILL, INK, 0, sw=0),
         f'<line x1="230" y1="50" x2="230" y2="{H - 10}" stroke="{INK}" stroke-width="1.6"/>',
         image_box(30, 70, 34, 30), text(76, 92, 'SubTracker', 18, 700)]
    for i, item in enumerate(menu):
        y = 130 + i * 46
        if item == active:
            p.append(rect(22, y - 4, 196, 38, '#d1d5db', INK, 6, sw=1.2))
        p.append(rect(34, y + 6, 18, 18, '#ffffff', MID, 3, sw=1.2))
        p.append(text(62, y + 21, item, 15, 600 if item == active else 400))
    p.append(f'<line x1="22" y1="{H - 110}" x2="218" y2="{H - 110}" stroke="{MID}"/>')
    p.append(text(34, H - 76, '○  Профиль', 15))
    p.append(text(34, H - 40, '→  Выйти', 15))
    p.append(text(260, 92, title, 26, 700))
    p.append(body)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'font-family="{FONT}"><rect width="100%" height="100%" fill="#fff"/>' + '\n'.join(p) + '</svg>')


def dashboard():
    b = [bar(260, 106, 300), button(1010, 66, 160, '+ Добавить')]
    labels = ['Активных подписок', 'Расходы в месяц', 'Расходы в год', 'Списано в месяце']
    for i, lab in enumerate(labels):
        x = 260 + i * 230
        b += [rect(x, 140, 210, 100), text(x + 16, 168, lab, 13, 400, 'start', '#4b5563'),
              text(x + 16, 208, '0 000 ₽', 26, 700), rect(x + 172, 190, 26, 26, FILL, MID, 6)]
    b += [rect(260, 262, 910, 64), text(280, 290, 'Месячный бюджет', 15, 700), text(1150, 290, '9 035 из 5 000 ₽', 14, 400, 'end'),
          rect(280, 302, 870, 10, LIGHT, MID, 5), rect(280, 302, 620, 10, '#6b7280', '#6b7280', 5)]
    b += [rect(260, 346, 540, 400), text(280, 378, 'Ближайшие списания (14 дней)', 16, 700), text(780, 378, 'Календарь', 14, 400, 'end')]
    for i in range(5):
        y = 400 + i * 68
        b += [f'<line x1="260" y1="{y - 6}" x2="800" y2="{y - 6}" stroke="{LIGHT}"/>', rect(280, y + 8, 40, 40, FILL, MID, 8),
              bar(336, y + 14, 160), bar(336, y + 34, 220, 8), bar(690, y + 14, 90), bar(650, y + 34, 130, 8)]
    b += [rect(820, 346, 350, 400), text(840, 378, 'Последние платежи', 16, 700)]
    for i in range(5):
        y = 400 + i * 68
        b += [f'<line x1="820" y1="{y - 6}" x2="1170" y2="{y - 6}" stroke="{LIGHT}"/>', bar(840, y + 14, 150), bar(840, y + 34, 110, 8), bar(1070, y + 14, 80)]
    return frame('Здравствуйте, {имя}!', 'subtracker/  — Главная', '\n'.join(b), 'Главная')


def subscription_list():
    b = [bar(260, 106, 140), button(1030, 66, 140, '+ Добавить'), rect(260, 140, 910, 84)]
    filters = [('Поиск', 210, 'Название сервиса'), ('Категория', 140, ''), ('Статус', 140, ''), ('Период', 140, ''), ('Сортировка', 130, '')]
    x = 278
    for lab, w, ph in filters:
        b.append(field(x, 168, w, lab, ph))
        x += w + 14
    b += [button(1114, 176, 40, '⌕', False), rect(260, 244, 910, 500)]
    cols = [('СЕРВИС', 280), ('КАТЕГОРИЯ', 450), ('СТОИМОСТЬ', 620), ('ПЕРИОД', 740), ('СЛЕД. СПИСАНИЕ', 860), ('СТАТУС', 1010)]
    for name, cx in cols:
        b.append(text(cx, 274, name, 12, 700, 'start', '#6b7280'))
    for i in range(7):
        y = 290 + i * 64
        b += [f'<line x1="260" y1="{y}" x2="1170" y2="{y}" stroke="{LIGHT}"/>', rect(280, y + 14, 36, 36, FILL, MID, 8),
              bar(326, y + 27, 100), bar(450, y + 27, 120), bar(620, y + 27, 70), bar(740, y + 27, 90), bar(860, y + 27, 90),
              rect(1010, y + 21, 80, 22, '#ffffff', MID, 11), rect(1102, y + 17, 26, 28, '#fff', MID, 4), rect(1134, y + 17, 26, 28, '#fff', MID, 4)]
    return frame('Мои подписки', 'subtracker/subscriptions/', '\n'.join(b), 'Подписки')


def subscription_form():
    b = [bar(260, 106, 280), rect(260, 140, 910, 610), text(284, 176, 'СЕРВИС И СТОИМОСТЬ', 13, 700, 'start', '#6b7280')]
    b += [field(284, 204, 420, 'Сервис *', 'Например, Кинопоиск'), field(724, 204, 420, 'Категория *', '— выберите —'),
          field(284, 276, 270, 'Стоимость *', '0,00'), field(574, 276, 270, 'Валюта *', 'RUB'), field(864, 276, 280, 'Период оплаты *', 'Ежемесячно'),
          text(284, 360, 'СРОКИ И СТАТУС', 13, 700, 'start', '#6b7280'),
          field(284, 388, 200, 'Статус *', 'Активна'), field(504, 388, 200, 'Дата начала *', 'дд.мм.гггг'),
          field(724, 388, 200, 'Следующее списание *', 'дд.мм.гггг'), field(944, 388, 200, 'Конец пробного', 'дд.мм.гггг'),
          field(284, 460, 200, 'Напомнить за (дней)', '3'), field(504, 460, 640, 'Сайт сервиса', 'https://'),
          text(284, 532, 'Заметки', 14, 600), rect(284, 540, 860, 110, '#ffffff', MID, 5),
          button(284, 680, 200, 'Добавить подписку'), button(500, 680, 110, 'Отмена', False)]
    return frame('Новая подписка', 'subtracker/subscriptions/new/', '\n'.join(b), 'Подписки')


def analytics():
    b = [bar(260, 106, 260), button(930, 66, 110, 'Excel', False), button(1060, 66, 110, 'CSV', False),
         rect(260, 140, 910, 80), field(280, 164, 220, 'С', 'дд.мм.гггг'), field(520, 164, 220, 'По', 'дд.мм.гггг'),
         button(760, 172, 140, 'Применить')]
    labels = ['Потрачено за период', 'В среднем в месяц', 'Количество списаний', 'К прошлому периоду']
    for i, lab in enumerate(labels):
        x = 260 + i * 230
        b += [rect(x, 236, 210, 84), text(x + 16, 262, lab, 14, 400, 'start', '#4b5563'), text(x + 16, 300, '00 000 ₽' if i < 2 else ('00' if i == 2 else '+0,0 %'), 24, 700)]
    b += [rect(260, 336, 590, 250), text(280, 366, 'Динамика расходов по месяцам', 16, 700)]
    heights = [40, 110, 60, 70, 80, 95, 150, 75, 100, 70, 65, 55]
    for i, h in enumerate(heights):
        b.append(rect(290 + i * 45, 566 - h, 30, h, '#9ca3af', '#6b7280', 3, sw=1))
    b.append(f'<line x1="280" y1="566" x2="830" y2="566" stroke="{INK}"/>')
    b += [rect(870, 336, 300, 250), text(890, 366, 'Структура по категориям', 16, 700),
          f'<circle cx="1020" cy="470" r="75" fill="none" stroke="#9ca3af" stroke-width="34"/>',
          f'<path d="M1020 395 A75 75 0 0 1 1093 488" fill="none" stroke="#4b5563" stroke-width="34"/>']
    b += [rect(260, 602, 590, 150), text(280, 632, 'Самые затратные подписки', 16, 700)]
    for i in range(3):
        y = 650 + i * 32
        b += [bar(280, y, 30), bar(330, y, 180), bar(560, y, 120), bar(740, y, 90)]
    b += [rect(870, 602, 300, 150), text(890, 632, 'Плановая нагрузка', 16, 700)]
    for i in range(3):
        y = 650 + i * 32
        b += [bar(890, y, 150), bar(1080, y, 70)]
    return frame('Аналитика расходов', 'subtracker/analytics/', '\n'.join(b), 'Аналитика')


if __name__ == '__main__':
    here = Path(__file__).parent
    for name, fn in [('wf_dashboard', dashboard), ('wf_subscriptions', subscription_list),
                     ('wf_subscription_form', subscription_form), ('wf_analytics', analytics)]:
        (here / f'{name}.svg').write_text(fn(), encoding='utf-8')
