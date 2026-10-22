from pydantic import BaseModel, Field, RootModel


class AISearchManifestColumn(BaseModel):
    name: str


class AISearchManifest(BaseModel):
    columns: list[AISearchManifestColumn]


class AISearchResult(BaseModel):
    data_array: list[list[object]] = Field(default_factory=list)


class AISearchResponse(BaseModel):
    manifest: AISearchManifest
    result: AISearchResult


class AISearchChunkRow(
    RootModel[
        tuple[
            str,
            str,
            str,
            str,
            int,
            str,
            float,
        ]
    ]
):
    pass
