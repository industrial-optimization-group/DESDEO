"""Tests for the pattern module."""

import pytest

from desdeo.tools.message import GeneratorMessageTopics, GenericMessage
from desdeo.tools.patterns import Publisher, createblanksubs

INTERESTED_TOPICS = [GeneratorMessageTopics.OBJECTIVES, GeneratorMessageTopics.TARGETS]
NOT_INTERESTED_TOPICS = [GeneratorMessageTopics.NEW_EVALUATIONS, GeneratorMessageTopics.POPULATION]
BlankSubscriber = createblanksubs(INTERESTED_TOPICS)


@pytest.mark.patterns
def test_publisher_subscriber():
    """Test whether a publisher and a subscriber can be initialized."""
    pub = Publisher()
    assert pub is not None
    sub = BlankSubscriber(publisher=pub)
    assert sub is not None


@pytest.mark.patterns
def test_post_init_runs_once_after_the_full_init_chain():
    """`__post_init__` must run exactly once, after the most derived `__init__` has returned."""
    pub = Publisher()

    class Middle(BlankSubscriber):
        def __init__(self, publisher: Publisher) -> None:
            super().__init__(publisher=publisher)
            self.tag = "middle"

    class Leaf(Middle):
        def __init__(self, publisher: Publisher) -> None:
            super().__init__(publisher=publisher)
            self.tag = "leaf"

    tags_at_post_init = []

    class Recording(Leaf):
        def __post_init__(self):
            tags_at_post_init.append(self.tag)
            super().__post_init__()

    Recording(publisher=pub)

    # One entry means it fired once for the three-deep chain; "leaf" means it fired last.
    assert tags_at_post_init == ["leaf"]


@pytest.mark.patterns
def test_construction_subscribes_and_registers():
    """A subscriber wires itself to its publisher as soon as it is constructed."""
    pub = Publisher()

    class Provider(BlankSubscriber):
        @property
        def provided_topics(self):
            return {0: NOT_INTERESTED_TOPICS}

    sub = Provider(publisher=pub)

    assert sub in pub.subscribers[INTERESTED_TOPICS[0]]
    assert sub in pub.subscribers[INTERESTED_TOPICS[1]]
    assert pub.registered_topics[NOT_INTERESTED_TOPICS[0]] == ["Provider"]


@pytest.mark.patterns
def test_registering_twice_is_a_no_op():
    """Subscribing an already subscribed object must not duplicate it, or it would be notified twice."""
    pub = Publisher()

    class Provider(BlankSubscriber):
        @property
        def provided_topics(self):
            return {0: NOT_INTERESTED_TOPICS}

    sub = Provider(publisher=pub)

    # The pattern used before subscribers registered themselves, and still found in user code.
    pub.auto_subscribe(sub)
    pub.register_topics(sub.provided_topics[sub.verbosity], sub.__class__.__name__)

    assert pub.subscribers[INTERESTED_TOPICS[0]] == [sub]
    assert pub.registered_topics[NOT_INTERESTED_TOPICS[0]] == ["Provider"]

    # A duplicate entry would show up as the same message delivered twice.
    message = [GenericMessage(topic=INTERESTED_TOPICS[0], value="message1", source="pytest")]
    pub.notify(message)
    assert sub.messages_received == message

    pub.subscribe(sub, "ALL")
    pub.subscribe(sub, "ALL")
    assert pub.global_subscribers == [sub]


@pytest.mark.patterns
def test_sub_unsub():
    """Test whether a subscriber can subscribe to and unsubscribe from a topic."""
    pub = Publisher()
    sub = BlankSubscriber(publisher=pub)

    # Subscribed by construction
    assert sub in pub.subscribers[sub.interested_topics[0]]
    assert sub in pub.subscribers[sub.interested_topics[1]]

    # Test unsubscribing from topics one by one
    pub.unsubscribe(sub, sub.interested_topics[0])
    assert sub not in pub.subscribers[sub.interested_topics[0]]
    assert sub in pub.subscribers[sub.interested_topics[1]]

    # Test unsubscribing from multiple topics
    pub.force_unsubscribe(sub)
    assert sub not in pub.subscribers[sub.interested_topics[1]]
    assert sub not in pub.subscribers[sub.interested_topics[0]]


@pytest.mark.patterns
def test_message_send():
    """Test whether a message can be sent to a subscriber."""
    pub = Publisher()
    sub = BlankSubscriber(publisher=pub)

    message = [
        GenericMessage(topic=GeneratorMessageTopics.OBJECTIVES, value="message1", source="pytest"),
        GenericMessage(topic=GeneratorMessageTopics.TARGETS, value="message2", source="pytest"),
    ]
    # Test direct message from publisher
    pub.notify(message)

    assert sub.messages_received == message

    # Test no message received when not subscribed
    pub.force_unsubscribe(sub)
    sub.messages_received = []

    message = [
        GenericMessage(topic=GeneratorMessageTopics.OBJECTIVES, value="message1", source="pytest"),
        GenericMessage(topic=GeneratorMessageTopics.TARGETS, value="message2", source="pytest"),
        GenericMessage(topic=GeneratorMessageTopics.NEW_EVALUATIONS, value="message3", source="pytest"),
    ]
    pub.notify(message)

    assert sub.messages_received == []

    # Test messages originating from pub after resubscribing
    pub.auto_subscribe(sub)

    pub.notify(message)
    assert GeneratorMessageTopics.NEW_EVALUATIONS not in [x.topic for x in sub.messages_received]

    assert sub.messages_received == message[:2]  # Only the first two messages should be received
