from app.services.openai_whisper import _map_openai_segments


def test_map_openai_segments_basic():
    segments = [
        {"id": 0, "start": 0.2, "end": 1.8, "text": "Hello world."},
        {"id": 1, "start": 2.0, "end": 3.4, "text": "Second line."},
    ]
    mapped = _map_openai_segments(segments)
    assert mapped == [
        {"id": 0, "start": 0.2, "end": 1.8, "text": "Hello world."},
        {"id": 1, "start": 2.0, "end": 3.4, "text": "Second line."},
    ]


def test_map_openai_segments_with_offset():
    segments = [{"id": 0, "start": 0.0, "end": 1.0, "text": "Chunk text"}]
    mapped = _map_openai_segments(segments, offset=10.0)
    assert mapped == [{"id": 0, "start": 10.0, "end": 11.0, "text": "Chunk text"}]
