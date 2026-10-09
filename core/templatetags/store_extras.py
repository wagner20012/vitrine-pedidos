from django import template

register = template.Library()


@register.filter
def digits_only(value):
    """Mantém apenas dígitos (para links wa.me)."""
    return "".join(ch for ch in str(value or "") if ch.isdigit())


@register.filter
def get_item(dictionary, key):
    """Acesso a dicionário em template: {{ mydict|get_item:key }}."""
    if hasattr(dictionary, "get"):
        return dictionary.get(key)
    return ""
