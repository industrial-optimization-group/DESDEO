"""This module contains voting rules for group decision making such as majority rule."""

from collections import Counter


def majority_rule(votes: dict[str, int]) -> int | None:
    """Choose the option that has more than half of the votes.

    Args:
        votes (dict[str, int]): A dictionary mapping voter IDs to their votes.

    Returns:
        int | None: The option that has more than half of the votes, or None if no such option exists.
    """
    counts = Counter(votes.values())
    all_votes = sum(counts.values())
    for vote, c in counts.items():
        if c > all_votes // 2:
            return vote
    return None


def plurality_rule(votes: dict[str, int]) -> list[int]:
    """Choose the option that has the most votes.

    Args:
        votes (dict[str, int]): A dictionary mapping voter IDs to their votes.

    Returns:
        list[int]: A list of options that have the most votes (in case of a tie).
    """
    counts = Counter(votes.values())
    max_votes = max(counts.values())
    return [vote for vote, c in counts.items() if c == max_votes]


def consensus_rule(votes: dict[str, int], min_votes: int) -> list[int]:
    """Choose all options that have at least min_votes votes.

    Args:
        votes (dict[str, int]): A dictionary mapping voter IDs to their votes.
        min_votes (int): The minimum number of votes required for an option to be selected.

    """
    if min_votes <= 0:
        raise ValueError("min_votes must be greater than 0.")
    if min_votes > len(votes):
        raise ValueError("min_votes cannot be greater than the number of voters.")
    counts = Counter(votes.values())
    return [vote for vote, c in counts.items() if c >= min_votes]
