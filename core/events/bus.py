from collections import defaultdict

class EventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)

    def subscribe(self, event_type, callback):
        self.subscribers[event_type].append(callback)

    def publish(self, event_type, *args, **kwargs):
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                callback(*args, **kwargs)
