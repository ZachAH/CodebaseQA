from rest_framework.throttling import AnonRateThrottle


class AskBurstThrottle(AnonRateThrottle):
    scope = "ask_burst"


class AskDayThrottle(AnonRateThrottle):
    scope = "ask_day"
