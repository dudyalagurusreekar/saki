import pytest
from pydantic import ValidationError
from backend.models.schemas import ChatRequest, ChatResponse
from backend.routes.chat import (
    get_conversations,
    search_conversations,
    get_conversation_history,
    create_new_conversation,
    delete_conversation,
    get_attachment_context,
    format_history_context,
    is_helpless_response
)


def test_chat_request_validation():
    # Valid request
    req = ChatRequest(message="Hello Saki", conversation_id="test-session")
    assert req.message == "Hello Saki"
    assert req.conversation_id == "test-session"

    # Empty message should raise ValidationError
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_helpless_response_detection():
    assert is_helpless_response("") is True
    assert is_helpless_response("short") is True
    assert is_helpless_response("I apologize, but I do not know the answer to this question.") is True
    assert is_helpless_response("Saki is a helpful AI companion built with FastAPI and Next.js.") is False


def test_history_formatting():
    history = [
        {"user": "Hi", "saki": "Hello!"},
        {"user": "How are you?", "saki": "I am great!"}
    ]
    fmt = format_history_context(history)
    assert "User: Hi" in fmt
    assert "Saki: Hello!" in fmt


def test_conversations_management():
    # Fetch conversations
    convs = get_conversations()
    assert "active_id" in convs
    assert "today" in convs
    assert "yesterday" in convs
    assert "older" in convs

    # Create new conversation
    new_conv = create_new_conversation()
    assert "id" in new_conv
    assert new_conv["title"] == "New Conversation"

    # Fetch detail
    detail = get_conversation_history(new_conv["id"])
    assert detail["id"] == new_conv["id"]

    # Search conversations
    search_res = search_conversations("Welcome")
    assert "results" in search_res

    # Delete conversation
    del_res = delete_conversation(new_conv["id"])
    assert del_res["deleted"] is True
    assert del_res["id"] == new_conv["id"]
