"""This module contains the classes for the publisher-subscriber (ish) pattern.

The pattern is used in the evolutionary algorithms to send messages between the different components. This allows
the components to be decoupled and the messages to be sent between them without the components knowing about each
other. The pattern closely resembles the publisher-subscriber pattern, with one key difference. The subscribers can
also create messages and send them to the publisher, which then forwards the messages to the other subscribers.

The pattern is implemented with two classes: `Subscriber` and `Publisher`. The `Subscriber` class is an abstract
class that must be inherited by the classes that want to receive (or send) messages. All evolutionary operators
must inherit the `Subscriber` class. Some objects that may be interested in the messages, but otherwise unrelated
to the evolutionary operators, may also inherit the `Subscriber` class. Examples of such objects are a logging class,
an archive class, or a class that visualizes intermediate results.

The `Publisher` class is a class that stores the subscribers and forwards the messages to them. The `Publisher` class
is not connected to the evolutionary algorithms and only serves as a message router. As mentioned earlier, the
components do not know about each other, and the `Publisher` class is the only class that knows about all the
connections in between components. The user of the evolutionary algorithms is responsible for creating the connections.
However, the implementations of the operators do provide default, so called topics that the operator must subscribe to.

The way the pattern works is as follows. Each operator has a `do` method which is called by the evolutionary algorithm
when the operator is to be executed. This method has some default arguments, depending upon the class of the operator.
E.g., the `do` method of the mutation related classes may have a default arguments as `offsprings` and `parents`, where
each is a tuple of decision variables, objectives, and constraints. However, some special mutation operator may require
additional inputs. E.g., an adaptive mutation operator may require the current generation number as an input. To provide
this additional input, we do not change the signature of the `do` method.

Instead, we let the mutation operator subscribe to a topic called, e.g., `current_generation`. The publisher, is then
responsible for sending the current generation number to the mutation operator, whenever the generation number changes.
The mutation operator can then update its internal state based on the received generation number.

To be able to send this informatiom, the `Publisher` class has a method called `notify`. Operators can call this method
to send messages to the subscribers. The idea is to do this at the end of the `do` method. That way, whenever any
operator is executed, it can send messages to the other operators (which have subscribed to the topics).

Note that the operators do not know about the other operators. The subscribers do not know the origin of the messages.
This decoupling allows for a more modular design and easier extensibility of the evolutionary algorithms.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class Subscriber(ABC):
    """Base class for both subscriber and message sender.

    These are used in the evoluationary algorithms to send messages between the different components. The pattern
    closely resembles the publisher-subscriber pattern, with one key difference. The subscribers can also create
    messages and send them to the publisher, which then forwards the messages to the other subscribers.
    """

    def __init__(self, publisher: Callable, topics: list[str] | None = None, verbosity: int = 1) -> None:
        """Initialize a subscriber.

        Args:
            publisher (Callable): the publisher to send messages to.
            topics (list[str] | None): the topics the subscriber is interested in. Check the documentation to see
                available topics. If the subscriber is interested in all topics, the list should contain "ALL".
                A user should not need to provide topics, as the operators provide default topics. Defaults to None,
                in which case the subscriber will not receive any messages.
            verbosity (int, optional): the verbosity level of the messages. Defaults to 1, which may mean differing
                amounts of information depending on the message sender. A value of 0 means no messages at all.
        """
        if topics is not None:
            if isinstance(topics, list):
                if not all(isinstance(elem, str) for elem in topics):
                    raise TypeError("Topics must be a list of strings.")
            else:
                raise TypeError("Topics must be a list of strings.")
        if not isinstance(verbosity, int):
            raise TypeError("Verbosity must be an integer.")
        self.publisher = publisher
        self.topics = topics if topics is not None else []
        self.verbosity = verbosity

    def notify(self) -> None:
        """Notify the publisher of changes in the subject.

        The contents of the message (a dictionary) are defined in the `state` method. The `state` method can return
        different messages depending on the verbosity level.
        """
        self.publisher.notify(messages=self.state())

    @abstractmethod
    def update(self, message: dict) -> None:
        """Update self as a result of messages from the publisher.

        Args:
            message (dict): the message from the publisher. Note that each message is a dictionary with a single
            key-value pair.
        """

    @abstractmethod
    def state(self) -> dict[str, Any]:
        """Return the state of the subject. This is the dictionary of messages to be sent to the subscribers."""


class Publisher:
    """Class for a publisher that sends messages to subscribers.

    The publisher is unconnected from the evolutionary algorithms and only serves as a message router. The subscribers
    can subscribe to different message keys and receive messages when the publisher receives a message with the
    corresponding key.
    """

    def __init__(self) -> None:
        """Initialize a blank publisher."""
        self.subscribers = {}
        self.global_subscribers = []

    def subscribe(self, subscriber: Subscriber, topic: str) -> None:
        """Store a subscriber for a given message key.

        Whenever the publisher receives a message with the given key, it will notify the subscriber. This method can
        be used to subscribe to multiple topics by calling it multiple times. Moreover, the user can force the
        subscriber to receive all messages by setting the topic to "ALL".

        Args:
            subscriber (Subscriber): the subscriber to notify.
            topic (str): the message topic (key in message dictionary) to subscribe to.
                If "ALL", the subscriber is notified of all messages.
        """
        if topic == "ALL":
            self.global_subscribers.append(subscriber)
            return
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(subscriber)

    def auto_subscribe(self, subscriber: Subscriber) -> None:
        """Store a subscriber for multiple message keys. The subscriber must have the topics attribute.

        Whenever the publisher receives a message with the given key, it will notify the subscriber.

        Args:
            subscriber (Subscriber): the subscriber to notify.
        """
        for topic in subscriber.topics:
            self.subscribe(subscriber, topic)

    def unsubscribe(self, subscriber: Subscriber, topic: str) -> None:
        """Remove a subscriber from a given message key.

        Args:
            subscriber (Subscriber): the subscriber to remove.
            topic (str): the key of the message to unsubscribe from.
        """
        if topic == "ALL":
            self.global_subscribers.remove(subscriber)
            return
        if topic in self.subscribers:
            self.subscribers[topic].remove(subscriber)

    def unsubscribe_multiple(self, subscriber: Subscriber, topics: list[str]) -> None:
        """Remove a subscriber from multiple message keys.

        Args:
            subscriber (Subscriber): the subscriber to remove.
            topics (list[str]): the keys of the messages to unsubscribe from.
        """
        for topic in topics:
            self.unsubscribe(subscriber, topic)

    def force_unsubscribe(self, subscriber: Subscriber) -> None:
        """Remove a subscriber from all message keys.

        Args:
            subscriber (Subscriber): the subscriber to remove.
        """
        for topic in self.subscribers:
            if subscriber in self.subscribers[topic]:
                self.subscribers[topic].remove(subscriber)

    def notify(self, messages: dict) -> None:
        """Notify subcribers of the received message/messages.

        Args:
            messages (dict): the messages to send to the subscribers. The keys of the message dictacte which subscribers
                are notified. Note that `messages` may contain multiple messages. The publisher will notify the
                subscribers of each message, one by one.
        """
        for topic in messages:
            # Notify global subscribers
            for subscriber in self.global_subscribers:
                subscriber.update({topic: messages[topic]})
            # Notify subscribers of the given key
            if topic in self.subscribers:
                for subscriber in self.subscribers[topic]:
                    subscriber.update({topic: messages[topic]})


class BlankSubscriber(Subscriber):
    """A simple subscriber for testing purposes."""

    def __init__(self, publisher: Callable, topics: list[str], verbosity: int = 1) -> None:
        """Initialize a subscriber."""
        super().__init__(publisher, topics, verbosity)
        self.messages_to_send = {}
        self.messages_received = {}

    def update(self, message: dict) -> None:
        """Update the internal state of the subscriber."""
        self.messages_received.update(message)

    def state(self) -> dict[str, Any]:
        """Return the internal state of the subscriber."""
        return self.messages_to_send
