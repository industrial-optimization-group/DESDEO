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

To be able to send this information, the `Publisher` class has a method called `notify`. Operators can call this method
to send messages to the subscribers. The idea is to do this at the end of the `do` method. That way, whenever any
operator is executed, it can send messages to the other operators (which have subscribed to the topics).

Note that the operators do not know about the other operators. The subscribers do not know the origin of the messages.
This decoupling allows for a more modular design and easier extensibility of the evolutionary algorithms.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from desdeo.tools.message import AllowedMessagesAtVerbosity, Message, MessageTopics


class Subscriber(ABC):
    """Base class for both subscriber and message sender.

    These are used in the evolutionary algorithms to send messages between the different components. The pattern
    closely resembles the publisher-subscriber pattern, with one key difference. The subscribers can also create
    messages and send them to the publisher, which then forwards the messages to the other subscribers.
    """

    @property
    @abstractmethod
    def interested_topics(self) -> Sequence[MessageTopics]:
        """Return the topics the subscriber is interested in."""

    @property
    @abstractmethod
    def provided_topics(self) -> dict[int, Sequence[MessageTopics]]:
        """Return the topics the subscriber provides to the publisher, grouped by verbosity level."""

    def __init__(
        self,
        publisher: "Publisher",
        verbosity: int,
    ) -> None:
        """Initialize a subscriber.

        Args:
            publisher (Callable): the publisher to send messages to.
            verbosity (int, optional): the verbosity level of the messages. A value of 0 means no messages at all.
        """
        if not isinstance(verbosity, int):
            raise TypeError("Verbosity must be an integer.")
        if verbosity < 0:
            raise ValueError("Verbosity must be a non-negative integer.")
        self.publisher = publisher
        self.verbosity: int = verbosity

    def notify(self) -> None:
        """Notify the publisher of changes in the subject.

        The contents of the message (a dictionary) are defined in the `state` method. The `state` method can return
        different messages depending on the verbosity level.
        """
        if self.verbosity not in AllowedMessagesAtVerbosity:
            raise ValueError(f"Verbosity level {self.verbosity} is not allowed.")
        if self.verbosity == 0:
            return

        state = self.state()
        if all(isinstance(x, AllowedMessagesAtVerbosity[self.verbosity]) for x in state):
            self.publisher.notify(messages=state)

    @abstractmethod
    def update(self, message: Message) -> None:
        """Update self as a result of messages from the publisher.

        Args:
            message (Message): the message from the publisher. Note that each message is a pydantic model with a topic,
                value, and a source.
        """

    @abstractmethod
    def state(self) -> Sequence[Message]:
        """Return the state of the subject. This is the list of messages to send to the publisher."""


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
        self.registered_topics: dict[MessageTopics, list[str]] = {}

    def subscribe(self, subscriber: Subscriber, topic: MessageTopics) -> None:
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
        for topic in subscriber.interested_topics:
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

    def register_topics(self, topics: list[MessageTopics], source: str) -> None:
        """Register topics provided to the publisher.

        Args:
            topics (list[MessageTopics]): the topics to register.
            source (str): the source of the topics.
        """
        for topic in topics:
            if topic not in self.registered_topics:
                self.registered_topics[topic] = [source]
            else:
                self.registered_topics[topic].append(source)

    def check_consistency(self) -> tuple[bool, dict[MessageTopics, list[str]]]:
        """Check if all subscribed topics have also been registered by a source.

        Returns:
            tuple[bool, dict[MessageTopics, list[str]]]: Returns a tuple. The first element is a bool. True if all
                subscribed topics have been registered by a source. False otherwise. The second element is a dictionary
                of unregistered topics that have been subscribed to.
        """
        unregistered_topics = {}
        for topic in self.subscribers:
            if topic not in self.registered_topics:
                unregistered_topics[topic] = [x.__class__.__name__ for x in self.subscribers[topic]]
        if unregistered_topics:
            return False, unregistered_topics
        return True, {}

    def relationship_map(self):
        """Make a diagram connecting sources to subscribers based on topics."""
        relationships = {}
        for topic in self.subscribers:
            for subscriber in self.subscribers[topic]:
                if topic.value not in relationships:
                    relationships[topic.value] = [(subscriber.__class__.__name__, self.registered_topics[topic])]
                else:
                    relationships[topic.value].append((subscriber.__class__.__name__, self.registered_topics[topic]))
        return relationships

    def notify(self, messages: Sequence[Message] | None) -> None:
        """Notify subscribers of the received message/messages.

        Args:
            messages (Sequence[BaseMessage]): the messages to send to the subscribers. Each message is a pydantic model
                with a topic, value, and a source.
        """
        if messages is None:
            return
        for message in messages:
            # Notify global subscribers
            for subscriber in self.global_subscribers:
                subscriber.update(message)
            # Notify subscribers of the given key
            if message.topic in self.subscribers:
                for subscriber in self.subscribers[message.topic]:
                    subscriber.update(message)


def createblanksubs(interested_topics: Sequence[MessageTopics]) -> type["Subscriber"]:
    """Create a blank subscriber for testing purposes.

    Args:
        interested_topics (list[MessageTopics]): the topics the subscriber is interested in.

    Returns:
        type[Subscriber]: the blank subscriber class.
    """

    class BlankSubscriber(Subscriber):
        """A simple subscriber for testing purposes."""

        @property
        def interested_topics(self) -> Sequence[MessageTopics]:
            """Return the topics the subscriber is interested in."""
            return interested_topics

        @property
        def provided_topics(self) -> dict[int, Sequence[MessageTopics]]:
            """Return the topics the subscriber provides to the publisher, grouped by verbosity level."""
            return {0: []}

        def __init__(self, publisher: "Publisher", verbosity: int = 0) -> None:
            """Initialize a subscriber."""
            super().__init__(publisher, verbosity)
            self.messages_to_send: list[Message] = []
            self.messages_received: list[Message] = []

        def update(self, message: Message) -> None:
            """Update the internal state of the subscriber."""
            self.messages_received.append(message)

        def state(self) -> list[Message]:
            """Return the internal state of the subscriber."""
            return self.messages_to_send

    return BlankSubscriber
