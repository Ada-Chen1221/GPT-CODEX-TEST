from scripts.run_batch import extract_structured


def test_extract_json_ok():
    out = extract_structured('{"answer":"ok","label":"positive"}', ["answer", "label"])
    assert out["answer"] == "ok"
    assert out["label"] == "positive"


def test_extract_fallback_text():
    out = extract_structured("plain text", ["answer", "label"])
    assert out["answer"] == "plain text"
    assert out["label"] is None
