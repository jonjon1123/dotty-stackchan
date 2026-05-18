"""Layer-6 proactive greeter — contextualised named greetings on
face_recognized events.

Pure lift of bridge/proactive_greeter.py with three adjustments:
  1. Subscribes to the PerceptionState bus directly (events are
     PerceptionEvent dataclasses, not dicts — handler uses attribute
     access).
  2. CalendarFacade adapter wraps the dotty-behaviour CalendarCache to
     satisfy the get_events / summarize_for_prompt interface the
     greeter expects.
  3. Default state path moved off the RPi's ~/.zeroclaw/ into
     /var/lib/dotty-behaviour/state/.
"""

from .calendar_facade import CalendarFacade
from .greeter import ProactiveGreeter

__all__ = ["CalendarFacade", "ProactiveGreeter"]
