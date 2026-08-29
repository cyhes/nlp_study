"""Unit tests for each role's parser (the fault-tolerant part)."""

from orchestrator.roles.base import get_role


def test_classification_parse():
    r = get_role("classification").parse('{"topic":"tech","intent":"inform"}')
    assert r["topic"] == "tech"
    assert r["intent"] == "inform"


def test_classification_parse_fallback():
    r = get_role("classification").parse("topic: sports intent: question")
    assert r["topic"] == "sports"


def test_ner_parse():
    r = get_role("ner").parse('{"entities":[{"text":"Alice","type":"PER"}]}')
    assert r["entities"][0]["text"] == "Alice"
    assert r["entities"][0]["type"] == "PER"


def test_ner_parse_fallback():
    r = get_role("ner").parse("Apple (ORG) and Bob (PER)")
    assert {"text": "Apple", "type": "ORG"} in r["entities"]


def test_summarization_parse_json():
    r = get_role("summarization").parse('{"summary":"short version"}')
    assert r["summary"] == "short version"


def test_summarization_parse_plain():
    r = get_role("summarization").parse("just some plain text")
    assert r["summary"] == "just some plain text"


def test_sentiment_parse():
    r = get_role("sentiment").parse('{"label":"positive","score":0.9}')
    assert r["label"] == "positive"
    assert r["score"] == 0.9


def test_sentiment_parse_fallback():
    r = get_role("sentiment").parse("this is clearly negative vibes")
    assert r["label"] == "negative"


def test_translation_parse():
    r = get_role("translation").parse('{"target_lang":"en","translation":"hi"}')
    assert r["translation"] == "hi"
