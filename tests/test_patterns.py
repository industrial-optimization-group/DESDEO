"""Tests for the pattern module."""

import pytest

from desdeo.tools.patterns import BlankSubscriber, Publisher


INTERESTED_TOPICS = ["topic1", "topic2"]
NOT_INTERESTED_TOPICS = ["topic3", "topic4"]


@pytest.mark.patterns
def test_publisher_subscriber():
    """Test whether a publisher and a subscriber can be initialized."""
    pub = Publisher()
    assert pub is not None

    sub = BlankSubscriber(pub, topics=INTERESTED_TOPICS)
    assert sub is not None


@pytest.mark.patterns
def test_sub_unsub():
    """Test whether a subscriber can subscribe to and unsubscribe from a topic."""
    pub = Publisher()
    sub = BlankSubscriber(pub, topics=INTERESTED_TOPICS)

    # Test subscribing to topics
    pub.auto_subscribe(sub, sub.topics)
    assert sub in pub.subscribers[sub.topics[0]]
    assert sub in pub.subscribers[sub.topics[1]]

    # Test unsubscribing from topics one by one
    pub.unsubscribe(sub, sub.topics[0])
    assert sub not in pub.subscribers[sub.topics[0]]
    assert sub in pub.subscribers[sub.topics[1]]

    # Test unsubscribing from multiple topics
    pub.force_unsubscribe(sub)
    assert sub not in pub.subscribers[sub.topics[1]]
    assert sub not in pub.subscribers[sub.topics[0]]


@pytest.mark.patterns
def test_message_send():
    """Test whether a message can be sent to a subscriber."""
    pub = Publisher()
    sub = BlankSubscriber(pub, topics=INTERESTED_TOPICS)

    pub.auto_subscribe(sub, sub.topics)

    message = {"topic1": "message1", "topic2": "message2"}
    # Test direct message from publisher
    pub.notify(message)

    assert sub.messages_received == message

    # Test no message received when not subscribed
    pub.force_unsubscribe(sub)
    sub.messages_received = {}

    message = {"topic1": "message1", "topic2": "message2"}
    pub.notify(message)

    assert sub.messages_received == {}

    # Test messages originating from a subscriber
    pub.auto_subscribe(sub, sub.topics)
    sub.messages_to_send = {"topic1": "message1", "topic2": "message2", "topic3": "message3"}

    sub.notify()
    assert "topic3" not in sub.messages_received

    assert sub.messages_received == {"topic1": "message1", "topic2": "message2"}
