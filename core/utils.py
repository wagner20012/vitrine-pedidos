from decimal import Decimal, ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")


def money(value) -> Decimal:
    """Arredonda um valor para 2 casas decimais (padrão monetário)."""
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def format_brl(value) -> str:
    """Formata um Decimal como R$ 1.234,56."""
    value = money(value)
    whole, cents = f"{value:.2f}".split(".")
    negative = whole.startswith("-")
    if negative:
        whole = whole[1:]
    thousands = []
    while len(whole) > 3:
        thousands.insert(0, whole[-3:])
        whole = whole[:-3]
    grouped = whole + (("." + ".".join(thousands)) if thousands else "")
    return f"{'-' if negative else ''}R$ {grouped},{cents}"
