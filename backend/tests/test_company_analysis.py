import pytest

from app.services.company_analysis import CompanyAnalysisService


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (0, "0円"),
        (999, "999円"),
        (10_000, "1万円"),
        (100_000_000, "1億円"),
        (1_000_000_000_000, "1兆円"),
        (
            2_313_051_000_000,
            "2兆3,130億5,100万円",
        ),
        (
            360_117_000_000,
            "3,601億1,700万円",
        ),
        (
            -100_000_000,
            "-1億円",
        ),
    ],
)
def test_format_yen(
    value: int | None,
    expected: str | None,
) -> None:
    service = CompanyAnalysisService()

    assert service.format_yen(value) == expected
    
    
from app.models.financial import FinancialHistory, FinancialYearValue


def test_build_financial_trend() -> None:
    service = CompanyAnalysisService()

    history = FinancialHistory(
        revenue=[
            FinancialYearValue(
                relative_year="前期",
                context_id="Prior1YearDuration",
                value=48_036_704_000_000,
                unit="円",
            ),
            FinancialYearValue(
                relative_year="当期",
                context_id="CurrentYearDuration",
                value=50_684_952_000_000,
                unit="円",
            ),
        ],
        operating_income=[
            FinancialYearValue(
                relative_year="前期",
                context_id="Prior1YearDuration",
                value=4_795_586_000_000,
                unit="円",
            ),
            FinancialYearValue(
                relative_year="当期",
                context_id="CurrentYearDuration",
                value=3_766_216_000_000,
                unit="円",
            ),
        ],
        net_income=[
            FinancialYearValue(
                relative_year="前期",
                context_id="Prior1YearDuration",
                value=4_765_086_000_000,
                unit="円",
            ),
            FinancialYearValue(
                relative_year="当期",
                context_id="CurrentYearDuration",
                value=3_848_098_000_000,
                unit="円",
            ),
        ],
        operating_cash_flow=[
            FinancialYearValue(
                relative_year="前期",
                context_id="Prior1YearDuration",
                value=3_696_934_000_000,
                unit="円",
            ),
            FinancialYearValue(
                relative_year="当期",
                context_id="CurrentYearDuration",
                value=5_472_920_000_000,
                unit="円",
            ),
        ],
    )

    trend = service.build_financial_trend(history)

    assert len(trend.years) == 5

    previous = trend.years[3]
    current = trend.years[4]

    assert previous.relative_year == "前期"
    assert current.relative_year == "当期"

    assert previous.operating_margin == 9.98
    assert previous.net_margin == 9.92
    assert previous.operating_cash_flow_margin == 7.7

    assert current.revenue_growth_rate == 5.51
    assert current.operating_income_growth_rate == -21.46
    assert current.net_income_growth_rate == -19.24

    assert current.operating_margin == 7.43
    assert current.net_margin == 7.59
    assert current.operating_cash_flow_margin == 10.8
    
from app.models.financial import FinancialTrend, FinancialTrendYear
from app.models.research_analysis import FinancialDisplayValues


def test_build_financial_analysis() -> None:
    service = CompanyAnalysisService()

    display_financials = FinancialDisplayValues(
        revenue="50兆6,849億5,200万円",
        operating_income="3兆7,662億1,600万円",
        profit_before_tax="5兆1,529億9,600万円",
        net_income="3兆8,480億9,800万円",
        total_assets="105兆5,223億3,100万円",
        operating_cash_flow="5兆4,729億2,000万円",
    )

    financial_trend = FinancialTrend(
        years=[
            FinancialTrendYear(
                relative_year="前期",
                revenue=48_036_704_000_000,
                operating_income=4_795_586_000_000,
                net_income=4_765_086_000_000,
                total_assets=93_601_350_000_000,
                operating_cash_flow=3_696_934_000_000,
                operating_margin=9.98,
                net_margin=9.92,
                operating_cash_flow_margin=7.7,
            ),
            FinancialTrendYear(
                relative_year="当期",
                revenue=50_684_952_000_000,
                operating_income=3_766_216_000_000,
                net_income=3_848_098_000_000,
                total_assets=105_522_331_000_000,
                operating_cash_flow=5_472_920_000_000,
                revenue_growth_rate=5.51,
                operating_income_growth_rate=-21.46,
                net_income_growth_rate=-19.24,
                operating_margin=7.43,
                net_margin=7.59,
                operating_cash_flow_margin=10.8,
            ),
        ]
    )

    result = service.build_financial_analysis(
        display_financials=display_financials,
        financial_trend=financial_trend,
    )

    assert result.summary == (
        "売上は50兆6,849億5,200万円、"
        "営業利益は3兆7,662億1,600万円、"
        "税引前利益は5兆1,529億9,600万円、"
        "純利益は3兆8,480億9,800万円、"
        "総資産は105兆5,223億3,100万円、"
        "営業活動によるキャッシュ・フローは"
        "5兆4,729億2,000万円です。"
    )

    assert result.notable_points == [
        "売上は前期比5.51%増加しました。",
        (
            "営業利益は前期比21.46%減少しました。"
            "営業利益率は9.98%から7.43%に低下しました。"
        ),
        (
            "純利益は前期比19.24%減少しました。"
            "純利益率は9.92%から7.59%に低下しました。"
        ),
        (
            "営業活動によるキャッシュ・フロー・マージンは"
            "7.70%から10.80%に上昇しました。"
        ),
        (
            "総資産は前期の93兆6,013億5,000万円から"
            "105兆5,223億3,100万円に増加しました。"
        ),
    ]

def test_build_financial_analysis_with_missing_values() -> None:
    service = CompanyAnalysisService()

    display_financials = FinancialDisplayValues(
        revenue="50兆6,849億5,200万円",
        operating_income=None,
        profit_before_tax=None,
        net_income=None,
        total_assets=None,
        operating_cash_flow=None,
    )

    financial_trend = FinancialTrend(
        years=[
            FinancialTrendYear(
                relative_year="前期",
                revenue=48_036_704_000_000,
                operating_income=None,
                net_income=None,
                total_assets=None,
                operating_cash_flow=None,
                operating_margin=None,
                net_margin=None,
                operating_cash_flow_margin=None,
            ),
            FinancialTrendYear(
                relative_year="当期",
                revenue=50_684_952_000_000,
                operating_income=None,
                net_income=None,
                total_assets=None,
                operating_cash_flow=None,
                revenue_growth_rate=5.51,
                operating_income_growth_rate=None,
                net_income_growth_rate=None,
                operating_margin=None,
                net_margin=None,
                operating_cash_flow_margin=None,
            ),
        ]
    )

    result = service.build_financial_analysis(
        display_financials=display_financials,
        financial_trend=financial_trend,
    )

    assert result.summary == (
        "売上は50兆6,849億5,200万円です。"
    )

    assert result.notable_points == [
        "売上は前期比5.51%増加しました。",
    ]

def test_build_financial_analysis_with_no_change() -> None:
    service = CompanyAnalysisService()

    display_financials = FinancialDisplayValues(
        revenue="1兆円",
    )

    financial_trend = FinancialTrend(
        years=[
            FinancialTrendYear(
                relative_year="前期",
                revenue=1_000_000_000_000,
                operating_margin=10.0,
                net_margin=8.0,
                operating_cash_flow_margin=12.0,
                total_assets=2_000_000_000_000,
            ),
            FinancialTrendYear(
                relative_year="当期",
                revenue=1_000_000_000_000,
                revenue_growth_rate=0.0,
                operating_margin=10.0,
                net_margin=8.0,
                operating_cash_flow_margin=12.0,
                total_assets=2_000_000_000_000,
            ),
        ]
    )

    result = service.build_financial_analysis(
        display_financials=display_financials,
        financial_trend=financial_trend,
    )

    assert result.notable_points == [
        "売上は前期比横ばいでした。",
        (
            "営業活動によるキャッシュ・フロー・マージンは"
            "12.00%で横ばいでした。"
        ),
        "総資産は前期と同額の2兆円でした。",
    ]