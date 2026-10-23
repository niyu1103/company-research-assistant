from app.models.company_fact import (
    CompanyFactAnswer,
    CompanyFactKey,
)
from app.models.research import CompanyResearchResult


class CompanyFactsService:
    def answer(
        self,
        *,
        research: CompanyResearchResult,
        question: str,
    ) -> CompanyFactAnswer:
        fact_key = self._detect_fact_key(question)

        if fact_key is None:
            return CompanyFactAnswer(
                fact_key=None,
                answer=("質問に対応する会社基本情報を特定できませんでした。"),
                insufficient_context=True,
            )

        company = research.company

        if fact_key == "employee_number":
            if company.employee_number is None:
                return self._missing(fact_key)

            return CompanyFactAnswer(
                fact_key=fact_key,
                answer=(f"{company.name}の従業員数は{company.employee_number}人です。"),
                insufficient_context=False,
            )

        if fact_key == "location":
            if company.location is None:
                return self._missing(fact_key)

            return CompanyFactAnswer(
                fact_key=fact_key,
                answer=(
                    f"{company.name}の登録されている所在地は{company.location}です。"
                ),
                insufficient_context=False,
            )

        if fact_key == "date_of_establishment":
            if company.date_of_establishment is not None:
                return CompanyFactAnswer(
                    fact_key=fact_key,
                    answer=(
                        f"{company.name}の設立日は{company.date_of_establishment}です。"
                    ),
                    insufficient_context=False,
                )

            if company.founding_year is not None:
                return CompanyFactAnswer(
                    fact_key=fact_key,
                    answer=(f"{company.name}の創業年は{company.founding_year}年です。"),
                    insufficient_context=False,
                )

            return self._missing(fact_key)

        if fact_key == "corporate_number":
            return CompanyFactAnswer(
                fact_key=fact_key,
                answer=(f"{company.name}の法人番号は{company.corporate_number}です。"),
                insufficient_context=False,
            )

        if fact_key == "representative_name":
            if company.representative_name is None:
                return self._missing(fact_key)

            return CompanyFactAnswer(
                fact_key=fact_key,
                answer=(f"{company.name}の代表者は{company.representative_name}です。"),
                insufficient_context=False,
            )

        if fact_key == "capital_stock":
            if company.capital_stock is None:
                return self._missing(fact_key)

            return CompanyFactAnswer(
                fact_key=fact_key,
                answer=(f"{company.name}の資本金は{company.capital_stock}です。"),
                insufficient_context=False,
            )

        return CompanyFactAnswer(
            fact_key=fact_key,
            answer=(f"{company.name}のEDINETコードは{research.edinet_code}です。"),
            insufficient_context=False,
        )

    def _detect_fact_key(
        self,
        question: str,
    ) -> CompanyFactKey | None:
        if any(
            keyword in question
            for keyword in (
                "従業員",
                "社員数",
                "従業員数",
            )
        ):
            return "employee_number"

        if any(
            keyword in question
            for keyword in (
                "所在地",
                "本社",
                "住所",
            )
        ):
            return "location"

        if any(
            keyword in question
            for keyword in (
                "設立",
                "創業",
            )
        ):
            return "date_of_establishment"

        if "法人番号" in question:
            return "corporate_number"

        if any(
            keyword in question
            for keyword in (
                "代表者",
                "社長",
            )
        ):
            return "representative_name"

        if "資本金" in question:
            return "capital_stock"

        if any(
            keyword in question
            for keyword in (
                "EDINETコード",
                "EDINET code",
                "edinet code",
            )
        ):
            return "edinet_code"

        return None

    def _missing(
        self,
        fact_key: CompanyFactKey,
    ) -> CompanyFactAnswer:
        return CompanyFactAnswer(
            fact_key=fact_key,
            answer=("取得した会社情報には、質問に必要なデータがありません。"),
            insufficient_context=True,
        )
