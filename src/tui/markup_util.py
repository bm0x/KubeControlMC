"""Utilidades de markup Rich seguras para la TUI.

La TUI usa widgets que parsean markup Rich (RichLog, Label, Static). Cualquier
contenido dinámico (output del servidor, túnel, nombres de jugadores, paths)
puede contener corchetes que rompen el markup y tiran MarkupError al renderizar.
Estas utilidades convierten contenido externo a texto plano seguro.
"""

import re

_TAG_RE = re.compile(r"\[/?[^\[\]\n]*\]")


def plain(text: str) -> str:
    """Extrae texto plano de un string que puede contener markup Rich.

    Nunca lanza excepciones: si el texto no es markup válido, se devuelve
    el texto original sin tags reconocibles.
    """
    text = text.replace(r"\[", "[").replace(r"\]", "]")
    return _TAG_RE.sub("", text)