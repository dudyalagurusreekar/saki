import pytest
from backend.routes.chat import (
    _load_conversations_data,
    create_new_conversation,
    get_conversations,
    search_conversations,
    delete_conversation,
    append_message_to_conversation
)


def test_create_and_append_conversation():
    new_conv = create_new_conversation()
    assert new_conv is not None
    conv_id = new_conv["id"]
    assert conv_id.startswith("conv-")

    append_message_to_conversation(
        conv_id=conv_id,
        user_msg="Testing conversational thread",
        assistant_msg="Got it, running tests!"
    )

    convs = get_conversations()
    assert convs is not None
    assert "today" in convs

    # Search
    search_res = search_conversations("Testing conversational thread")
    assert len(search_res["results"]) > 0
    assert any(r["id"] == conv_id for r in search_res["results"])

    # Clean up test conversation
    delete_conversation(conv_id)
