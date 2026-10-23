from typing import Protocol


class DocumentIndexSyncRepository(Protocol):
    def sync_and_wait(self) -> None: ...
