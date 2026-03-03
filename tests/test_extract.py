from scripts.run_batch import extract_attitude_score, extract_structured


def test_extract_json_ok():
    out = extract_structured('{"attitude_score":8}', ["attitude_score"])
    assert out["attitude_score"] == 8


def test_extract_fallback_score_from_text():
    text = "我整体偏支持，分数是 7。"
    out = extract_structured(text, ["attitude_score"])
    assert out["attitude_score"] == 7


def test_extract_attitude_score_none_when_missing():
    assert extract_attitude_score("没有给出数字") is None
