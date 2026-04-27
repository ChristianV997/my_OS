"""backend.pubsub — unified pub/sub abstraction for the MarketOS event bus.

All runtime components publish through ``broker`` and all consumers
(WebSocket stream, task inventory broadcaster, tests) subscribe through it.
"""
from backend.pubsub.broker import EventEnvelope, PubSubBroker, broker

__all__ = ["EventEnvelope", "PubSubBroker", "broker"]
