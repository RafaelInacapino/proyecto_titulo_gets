from django import template
register = template.Library()

@register.filter
def icon_class(status):
    mapping = {
        "online": "fa-check-circle text-success",
        "offline": "fa-times-circle text-danger",
        "error": "fa-exclamation-triangle text-warning",
    }
    return mapping.get(status, "fa-question-circle text-muted")

@register.filter
def badge_class(status):
    mapping = {
        "online": "badge-success",
        "offline": "badge-danger",
        "error": "badge-warning",
    }
    return mapping.get(status, "badge-secondary")
