from backend.app import wer


def test_dataset_size():
    assert len(wer.DATASET) == 20
