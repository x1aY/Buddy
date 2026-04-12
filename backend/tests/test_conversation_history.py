import pytest
from services.llm.conversation_history import ConversationHistory
from models.schemas import ConversationMessage


def test_conversation_history_add_message():
    history = ConversationHistory(max_messages=50)
    msg = ConversationMessage(
        id="test-1",
        role="user",
        text="hello",
        timestamp=12345
    )
    history.add_message(msg)
    assert len(history.get_messages()) == 1
    assert history.get_messages()[0].text == "hello"


def test_conversation_history_trimming():
    history = ConversationHistory(max_messages=3)
    for i in range(5):
        msg = ConversationMessage(
            id=f"test-{i}",
            role="user",
            text=f"message {i}",
            timestamp=12345 + i
        )
        history.add_message(msg)
    assert len(history) == 3
    # 保留最后 3 条：message 2, 3, 4
    messages = history.get_messages()
    assert messages[0].text == "message 2"
    assert messages[-1].text == "message 4"


def test_conversation_history_clear():
    history = ConversationHistory(max_messages=10)
    # Add a few messages
    for i in range(3):
        msg = ConversationMessage(
            id=f"test-{i}",
            role="user",
            text=f"message {i}",
            timestamp=12345 + i
        )
        history.add_message(msg)
    assert len(history) == 3
    # Clear
    history.clear()
    assert len(history) == 0
    assert len(history.get_messages()) == 0


def test_conversation_history_max_messages_1():
    history = ConversationHistory(max_messages=1)
    # Add multiple messages
    for i in range(5):
        msg = ConversationMessage(
            id=f"test-{i}",
            role="user",
            text=f"message {i}",
            timestamp=12345 + i
        )
        history.add_message(msg)
    # Should only keep the last message
    assert len(history) == 1
    messages = history.get_messages()
    assert messages[0].text == "message 4"


def test_conversation_history_empty_history():
    history = ConversationHistory(max_messages=10)
    assert len(history) == 0
    assert history.get_messages() == []


def test_conversation_history_validation_negative():
    with pytest.raises(ValueError):
        ConversationHistory(max_messages=0)
    with pytest.raises(ValueError):
        ConversationHistory(max_messages=-10)
    # Positive should work
    ConversationHistory(max_messages=1)
    ConversationHistory(max_messages=100)
