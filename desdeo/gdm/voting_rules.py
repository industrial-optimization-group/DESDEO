""" This module contains voting rules for group decision making such as majority rule. """

from collections import Counter


def majority_rule(votes: dict[str, int]):
    """
        TODO: docs
    """

    counts = Counter(votes.values())
    all_votes = sum(counts.values())
    for vote, c in counts.items():
        if c > all_votes // 2:
            return vote
    return None

def plurality_rule(votes: dict[str, int]):
    """
        TODO: docs
    """

    counts = Counter(votes.values())
    max_votes = max(counts.values())
    winners = [vote for vote, c in counts.items() if c == max_votes]

    return winners