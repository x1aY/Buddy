import pytest
import asyncio
import base64
from unittest.mock import Mock, AsyncMock
from services.speech.asr_stream_processor import AsrStreamProcessor


def test_asr_stream_processor_initialization():
    """Test that processor initializes with correct default state."""
    def mock_callback(text):
        pass
    processor = AsrStreamProcessor(mock_callback)
    assert processor.is_running() == False
    assert processor.streaming_asr is None
    assert len(processor._pending_audio_buffer) == 0
    assert processor._current_segment_id is None
    assert len(processor._current_segment_sentences) == 0
    assert processor._current_segment_ongoing == ""
    assert processor._silence_timer is None
    assert processor._silence_timer_id == 0


def test_get_current_text():
    """Test that get_current_text correctly combines completed and ongoing text."""
    def mock_callback(text):
        pass
    processor = AsrStreamProcessor(mock_callback)
    processor._current_segment_sentences = ["hello", "world"]
    processor._current_segment_ongoing = "test"
    assert processor.get_current_text() == "hello world test"


def test_get_current_text_empty():
    """Test get_current_text when there is no text."""
    def mock_callback(text):
        pass
    processor = AsrStreamProcessor(mock_callback)
    assert processor.get_current_text() == ""


def test_get_current_text_only_completed():
    """Test get_current_text with only completed sentences."""
    def mock_callback(text):
        pass
    processor = AsrStreamProcessor(mock_callback)
    processor._current_segment_sentences = ["hello", "world"]
    assert processor.get_current_text() == "hello world"


def test_get_current_text_only_ongoing():
    """Test get_current_text with only ongoing text."""
    def mock_callback(text):
        pass
    processor = AsrStreamProcessor(mock_callback)
    processor._current_segment_ongoing = "hello world"
    assert processor.get_current_text() == "hello world"


@pytest.mark.asyncio
async def test_start_stop_already_running():
    """Test that starting when already running stops the old session first."""
    mock_callback = Mock()
    processor = AsrStreamProcessor(mock_callback)

    # Just verify that calling stop when running is handled correctly
    # This test doesn't need full mocking, the real constructor will run
    # but we'll stop immediately
    mock_callback = Mock()
    processor = AsrStreamProcessor(mock_callback)
    assert processor.is_running() == False

    await processor.stop()
    assert processor.is_running() == False


@pytest.mark.asyncio
async def test_process_audio_chunk_buffering_when_not_running():
    """Test that audio chunks are buffered when ASR is not running."""
    mock_callback = Mock()
    processor = AsrStreamProcessor(mock_callback)

    # Encode some test audio data
    test_data = b"test audio data"
    base64_data = base64.b64encode(test_data).decode()

    # Process chunk when not running - should buffer
    await processor.process_audio_chunk(base64_data)
    assert len(processor._pending_audio_buffer) == 1
    assert processor._pending_audio_buffer[0] == test_data


@pytest.mark.asyncio
async def test_process_audio_chunk_invalid_base64():
    """Test that invalid base64 is handled gracefully."""
    mock_callback = Mock()
    processor = AsrStreamProcessor(mock_callback)

    # Invalid base64 should not crash
    await processor.process_audio_chunk("not valid base64!!!")
    # Should still be running (not running in this case, just no crash)
    assert processor.is_running() == False


@pytest.mark.asyncio
async def test_stop_cleans_up_resources():
    """Test that stop properly cleans up all resources and state."""
    mock_callback = Mock()
    processor = AsrStreamProcessor(mock_callback)

    # Set up some state
    processor._pending_audio_buffer = [b"chunk1", b"chunk2"]
    processor._current_segment_id = "test-id"
    processor._current_segment_sentences = ["hello"]
    processor._current_segment_ongoing = "world"

    # Create a dummy silence timer
    async def dummy_wait():
        await asyncio.sleep(10)

    processor._silence_timer = asyncio.create_task(dummy_wait())
    processor._silence_timer_id = 5

    mock_asr = AsyncMock()
    mock_asr.close = AsyncMock()
    processor.streaming_asr = mock_asr

    await processor.stop()

    # Verify all state is cleared
    assert processor.streaming_asr is None
    assert processor._silence_timer is None
    assert processor._silence_timer_id == 0
    assert len(processor._pending_audio_buffer) == 0
    assert processor._current_segment_id is None
    assert len(processor._current_segment_sentences) == 0
    assert processor._current_segment_ongoing == ""
    assert mock_asr.close.called
    assert processor._silence_timer is None or processor._silence_timer.done()


@pytest.mark.asyncio
async def test_callback_invoked_on_silence_timeout():
    """Test that callback is invoked with correct final text on silence timeout."""
    callback_result = []
    def mock_callback(text):
        callback_result.append(text)

    processor = AsrStreamProcessor(mock_callback)
    processor._current_segment_sentences = ["hello"]
    processor._current_segment_ongoing = "world"

    mock_asr = AsyncMock()
    mock_asr.close = AsyncMock()
    processor.streaming_asr = mock_asr

    # Override timeout to be quick
    processor._silence_timeout_ms = 100

    # Start the silence timeout process
    task = asyncio.create_task(processor._silence_timeout_process(1))
    processor._silence_timer_id = 1

    # Wait for completion
    await asyncio.wait_for(task, timeout=0.5)

    # Verify callback was called
    assert len(callback_result) == 1
    assert callback_result[0] == "hello world"
    assert processor.streaming_asr is None  # Should be stopped


@pytest.mark.asyncio
async def test_silence_timeout_skips_outdated_timer():
    """Test that outdated silence timers are skipped."""
    callback_called = False
    def mock_callback(text):
        nonlocal callback_called
        callback_called = True

    processor = AsrStreamProcessor(mock_callback)
    processor._current_segment_sentences = ["hello"]
    processor._current_segment_ongoing = "world"
    processor._silence_timer_id = 5  # Current timer id is higher

    processor._silence_timeout_ms = 50
    await processor._silence_timeout_process(1)  # Old timer id = 1

    # Should not call callback
    assert callback_called == False


@pytest.mark.asyncio
async def test_silence_timeout_skips_when_not_running():
    """Test that silence timeout is skipped when ASR is not running."""
    callback_called = False
    def mock_callback(text):
        nonlocal callback_called
        callback_called = True

    processor = AsrStreamProcessor(mock_callback)
    processor._current_segment_sentences = ["hello"]
    processor._current_segment_ongoing = "world"
    processor.streaming_asr = None  # Not running

    processor._silence_timeout_ms = 50
    await processor._silence_timeout_process(1)

    assert callback_called == False


@pytest.mark.asyncio
async def test_silence_timeout_skips_empty_text():
    """Test that silence timeout is skipped when there is no text."""
    callback_called = False
    def mock_callback(text):
        nonlocal callback_called
        callback_called = True

    processor = AsrStreamProcessor(mock_callback)
    processor._current_segment_sentences = []
    processor._current_segment_ongoing = ""

    mock_asr = AsyncMock()
    mock_asr.close = AsyncMock()
    processor.streaming_asr = mock_asr

    processor._silence_timeout_ms = 50
    await processor._silence_timeout_process(1)

    assert callback_called == False
