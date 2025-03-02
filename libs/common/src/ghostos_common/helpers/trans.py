from gettext import dgettext, dngettext

__all__ = ['GHOSTOS_DOMAIN', 'gettext', 'ngettext']

GHOSTOS_DOMAIN = 'ghostos'


def gettext(message):
    return dgettext(GHOSTOS_DOMAIN, message)


def ngettext(singular, plural, n):
    return dngettext(GHOSTOS_DOMAIN, singular, plural, n)
