from gettext import dgettext, dngettext

__all__ = ['GHOSTOS_DOMAIN', 'gettext', 'ngettext', 'get_current_locale']

GHOSTOS_DOMAIN = 'ghostos'


def gettext(message):
    return dgettext(GHOSTOS_DOMAIN, message)


def ngettext(singular, plural, n):
    return dngettext(GHOSTOS_DOMAIN, singular, plural, n)


def get_current_locale() -> str:
    from babel import default_locale
    return default_locale()


if __name__ == '__main__':
    print(get_current_locale())