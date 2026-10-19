import csv
import io
import zipfile

import httpx

from app.settings import get_settings


BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"

EDINET_CODE_LIST_URL = (
    "https://disclosure2dl.edinet-fsa.go.jp/"
    "searchdocument/codelist/Edinetcode.zip"
)


class EdinetClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.edinet_api_key

    async def get_documents(
        self,
        date: str,
    ) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/documents.json",
                params={
                    "date": date,
                    "type": 2,
                    "Subscription-Key": self.api_key,
                },
                timeout=30.0,
            )

            response.raise_for_status()

            return response.json()

    async def get_edinet_code(
        self,
        corporate_number: str,
    ) -> str | None:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                EDINET_CODE_LIST_URL,
                timeout=30.0,
            )

            response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            csv_names = [
                name
                for name in zip_file.namelist()
                if name.lower().endswith(".csv")
            ]

            if not csv_names:
                return None

            raw = zip_file.read(csv_names[0])

        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp932")

        rows = list(csv.reader(io.StringIO(text)))

        if len(rows) < 3:
            return None

        headers = rows[1]

        try:
            edinet_code_index = headers.index("ＥＤＩＮＥＴコード")
        except ValueError:
            edinet_code_index = headers.index("EDINETコード")

        corporate_number_index = headers.index("提出者法人番号")

        for row in rows[2:]:
            if len(row) <= corporate_number_index:
                continue

            if row[corporate_number_index] == corporate_number:
                return row[edinet_code_index]

        return None