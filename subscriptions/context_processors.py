def notifications_counter(request):
    """Добавляет во все шаблоны количество непрочитанных уведомлений."""
    if request.user.is_authenticated:
        return {'unread_notifications': request.user.notifications.filter(is_read=False).count()}
    return {'unread_notifications': 0}


# Какой пункт бокового меню подсвечивать для каждого маршрута
NAV_SECTIONS = {
    'subscriptions:dashboard': 'dashboard',
    'subscriptions:list': 'subscriptions', 'subscriptions:detail': 'subscriptions',
    'subscriptions:create': 'subscriptions', 'subscriptions:update': 'subscriptions',
    'subscriptions:delete': 'subscriptions',
    'subscriptions:calendar': 'calendar',
    'subscriptions:payments': 'payments', 'subscriptions:payment_create': 'payments',
    'subscriptions:payment_update': 'payments',
    'subscriptions:notifications': 'notifications',
}


def active_nav(request):
    """Определяет активный раздел меню по имени текущего маршрута."""
    match = getattr(request, 'resolver_match', None)
    if match is None:
        return {'nav': ''}
    if match.namespace in ('analytics', 'management_panel', 'accounts'):
        return {'nav': match.namespace}
    return {'nav': NAV_SECTIONS.get(match.view_name, '')}
