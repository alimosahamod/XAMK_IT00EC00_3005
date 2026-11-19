import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Ein Handler ist irgendeine Funktion, die ein Event entgegennimmt.
Handler = Callable[[Any], None]


class EventBus:
    """Subject im Observer Pattern: in-process Publish/Subscribe.

    Publisher rufen nur `publish(event)` auf und kennen ihre Subscriber nicht.
    Subscriber melden sich mit `subscribe(EventKlasse, handler)` an.
    Handler einer Event-Klasse laufen in Anmelde-Reihenfolge. Ein
    `unsubscribe` gibt es bewusst nicht (der Bus lebt nur pro Request).
    """

    def __init__(self) -> None:
        # Event-Klasse -> Liste der Handler, in Anmelde-Reihenfolge.
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: object) -> None:
        # Exakte Klasse als Schluessel: ReadingCreated erreicht nur ReadingCreated-Handler.
        for handler in list(self._handlers[type(event)]):
            try:
                handler(event)
            except Exception:
                # Ein fehlerhafter Subscriber wird geloggt; die uebrigen laufen weiter
                # und der Publisher (z.B. der gespeicherte Messwert) bleibt erfolgreich.
                logger.exception("Subscriber %r failed for %s", handler, type(event).__name__)
