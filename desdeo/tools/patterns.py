from abc import ABC, abstractmethod
from collections.abc import Callable


class Subscriber(ABC):
    """Base class for both subscriber and msg sender."""

    def __init__(self, publisher: Callable, verbosity: int = 1) -> None:
        """Initialize a subscriber.

        Args:
            publisher (Callable): the publisher to send messages to.
            verbosity (int, optional): the verbosity level of the messages. Defaults to 1, which may mean differing
                amounts of information depending on the message sender. A value of 0 means no messages at all.
        """
        self.publisher = publisher
        self.verbosity = verbosity

    def notify(self, **kwargs) -> None:
        """Notify the publisher of changes in the subject.

        The contents of the message (a dictionary) are defined in the `state` method. The `state` method can return
        different messages depending on the verbosity level.
        """
        self.publisher.notify(msg=self.state(), **kwargs)

    @abstractmethod
    def update(self, msg: dict) -> None:
        """Update self as a result of changes in the subject.

        Args:
            msg (dict): the msg from the subject.
        """

    @abstractmethod
    def state(self) -> dict:
        """Return the state of the subject. This is the msg to be sent to the subscribers."""


class Publisher:
    """Class for a publisher that sends messages to subscribers."""

    def __init__(self) -> None:
        """Initialize a blank publisher."""
        self.subscribers = {}
        self.global_subscribers = []

    def subscribe(self, subscriber: Subscriber, msg_key: str) -> None:
        """Store a subscriber for a given message key.

        Whenever the publisher receives a message with the given key, it will notify the subscriber.

        Args:
            subscriber (Subscriber): the subscriber to notify.
            msg_key (str): the key of the message to subscribe to. If "ALL", the subscriber is notified of all messages.
        """
        if msg_key == "ALL":
            self.global_subscribers.append(subscriber)
            return
        if msg_key not in self.subscribers:
            self.subscribers[msg_key] = []
        self.subscribers[msg_key].append(subscriber)

    def unsubscribe(self, subscriber: Subscriber, msg_key: str) -> None:
        """Remove a subscriber from a given message key.

        Args:
            subscriber (Subscriber): the subscriber to remove.
            msg_key (str): the key of the message to unsubscribe from.
        """
        if msg_key == "ALL":
            self.global_subscribers.remove(subscriber)
            return
        if msg_key in self.subscribers:
            self.subscribers[msg_key].remove(subscriber)

    def force_unsubscribe(self, subscriber: Subscriber) -> None:
        """Remove a subscriber from all message keys.

        Args:
            subscriber (Subscriber): the subscriber to remove.
        """
        for msg_key in self.subscribers:
            if subscriber in self.subscribers[msg_key]:
                self.subscribers[msg_key].remove(subscriber)

    def notify(self, msg: dict) -> None:
        """Notify subcribers of the received message/messages.

        Args:
            msg (dict): the messages to send to the subscribers. The keys of the message dictacte which subscribers
                are notified.
        """
        for msg_key in msg:
            # Notify global subscribers
            for subscriber in self.global_subscribers:
                subscriber.update({msg_key: msg[msg_key]})
            # Notify subscribers of the given key
            if msg_key in self.subscribers:
                for subscriber in self.subscribers[msg_key]:
                    subscriber.update({msg_key: msg[msg_key]})
