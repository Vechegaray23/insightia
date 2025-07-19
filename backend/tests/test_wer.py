from backend.app import wer


def test_wer_exact():
    assert wer.wer("hola mundo", "hola mundo") == 0.0


def test_wer_single_error():
    score = wer.wer("hola mundo", "hola")
    assert score == 1 / 2
