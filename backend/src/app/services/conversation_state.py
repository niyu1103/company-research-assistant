from app.models.conversation_state import (
    ConversationState,
)


class ConversationStateService:
    def __init__(self) -> None:
        self._states: dict[
            str,
            ConversationState,
        ] = {}

    def get(
        self,
        conversation_id: str,
    ) -> ConversationState | None:
        return self._states.get(conversation_id)

    def save(
        self,
        state: ConversationState,
    ) -> None:
        self._states[state.conversation_id] = state

    def delete(
        self,
        conversation_id: str,
    ) -> None:
        self._states.pop(
            conversation_id,
            None,
        )
