from django import template

register = template.Library()


@register.filter
def status_to_step(status):
    return {
        "open": 1,
        "filed": 1,
        "assigned": 2,
        "in_progress": 3,
        "work": 4,
        "resolved": 5,
        "closed": 5,
    }.get((status or "").lower(), 1)
