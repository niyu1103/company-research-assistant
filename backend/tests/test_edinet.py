from app.clients.edinet import EdinetClient
from app.models.edinet import EdinetCsvRow


def test_financial_history_matches_non_consolidated_context() -> None:
    client = EdinetClient()

    rows = [
        EdinetCsvRow(
            element_id=(
                "jpcrp_cor:"
                "NetSalesSummaryOfBusinessResults"
            ),
            item_name="売上高、経営指標等",
            context_id=(
                "CurrentYearDuration_"
                "NonConsolidatedMember"
            ),
            relative_year="当期",
            consolidated_or_non_consolidated="その他",
            period_type="期間",
            unit="円",
            value="1153196000",
        ),
    ]

    values = client._find_metric_history(
        rows=rows,
        element_names=(
            "NetSalesSummaryOfBusinessResults",
        ),
        context_suffix="Duration",
    )

    assert len(values) == 1
    assert values[0].value == 1153196000
    assert values[0].relative_year == "当期"
    assert values[0].context_id.startswith(
        "CurrentYearDuration"
    )