"""Tests for the pattern module."""

import pytest

from desdeo.tools.message import GeneratorMessageTopics, GenericMessage
from desdeo.tools.patterns import BlankSubscriber, Publisher

INTERESTED_TOPICS = [GeneratorMessageTopics.OBJECTIVES, GeneratorMessageTopics.TARGETS]
NOT_INTERESTED_TOPICS = [GeneratorMessageTopics.NEW_EVALUATIONS, GeneratorMessageTopics.POPULATION]


@pytest.mark.patterns
def test_publisher_subscriber():
    """Test whether a publisher and a subscriber can be initialized."""
    pub = Publisher()
    assert pub is not None

    sub = BlankSubscriber(publisher=pub, topics=INTERESTED_TOPICS)
    assert sub is not None


@pytest.mark.patterns
def test_sub_unsub():
    """Test whether a subscriber can subscribe to and unsubscribe from a topic."""
    pub = Publisher()
    sub = BlankSubscriber(publisher=pub, topics=INTERESTED_TOPICS)

    # Test subscribing to topics
    pub.auto_subscribe(sub)
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
    sub = BlankSubscriber(pub, topics=INTERESTED_TOPICS)

    pub.auto_subscribe(sub)

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
    ]
    pub.notify(message)

    assert sub.messages_received == []

    # Test messages originating from a  (kinda circular here)
    pub.auto_subscribe(sub)
    sub.messages_to_send = [
        GenericMessage(topic=GeneratorMessageTopics.OBJECTIVES, value="message1", source="pytest"),
        GenericMessage(topic=GeneratorMessageTopics.TARGETS, value="message2", source="pytest"),
        GenericMessage(topic=GeneratorMessageTopics.NEW_EVALUATIONS, value="message3", source="pytest"),
    ]

    message = [
        GenericMessage(topic=GeneratorMessageTopics.OBJECTIVES, value="message1", source="pytest"),
        GenericMessage(topic=GeneratorMessageTopics.TARGETS, value="message2", source="pytest"),
    ]

    sub.notify()
    assert GeneratorMessageTopics.NEW_EVALUATIONS not in [x.topic for x in sub.messages_received]

    assert sub.messages_received == message
