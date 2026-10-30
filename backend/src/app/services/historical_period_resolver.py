from agents import Agent, Runner

from app.models.historical_period import (
    HistoricalPeriodResolution,
)


class HistoricalPeriodResolverService:
    def __init__(self) -> None:
        self.agent = Agent(
            name="Historical Period Resolver",
            model="gpt-5.6-luna",
            instructions="""
あなたは歴史的・社会的・経済的な出来事や期間表現を、
財務分析で利用できる西暦年の範囲へ変換するResolverです。

入力例:
- コロナ禍
- リーマンショック
- 東日本大震災直後
- アベノミクス初期
- 半導体不足の時期

以下を返してください。

label:
入力された期間・出来事を簡潔に表す名称。

resolved:
財務分析に使用できる年単位の代表期間を、
十分な確度で設定できる場合は true。

start_year:
代表期間の開始年。

end_year:
代表期間の終了年。

reason:
その年範囲を採用した理由を簡潔に説明する。
厳密な境界に幅がある場合は、そのことも明記する。

重要:
- 日付や月まで厳密に一意である必要はない。
- 厳密な開始日・終了日は文脈によって異なっていても、
  年単位の代表期間として一般的に妥当な範囲を設定できる場合は
  resolved=true とする。
- その場合は reason に
  「厳密な終期には幅があるが、財務分析上の代表期間として扱う」
  ことを明記する。
- 年単位でも合理的な期間を決められない場合は
  resolved=false とする。
- 曖昧すぎる表現を無理に解決しない。
- start_year は end_year 以下でなければならない。
- 回答や財務分析そのものは行わない。
- 期間の解決だけを行う。

判断例:

「コロナ禍」
→ resolved=true
→ start_year=2020
→ end_year=2023
→ 厳密な終期には地域・文脈による差があるが、
  財務分析上の代表期間として2020年から2023年を使用する。

「リーマンショック」
→ resolved=true
→ start_year=2008
→ end_year=2009

「景気が少し悪かった頃」
→ 年単位の期間を合理的に特定できないため
  resolved=false
""",
            output_type=HistoricalPeriodResolution,
        )

    async def resolve(
        self,
        period_hint: str,
    ) -> HistoricalPeriodResolution:
        result = await Runner.run(
            self.agent,
            period_hint,
        )

        resolution = HistoricalPeriodResolution.model_validate(result.final_output)

        if not resolution.resolved:
            return resolution

        if resolution.start_year is None or resolution.end_year is None:
            return HistoricalPeriodResolution(
                label=resolution.label,
                resolved=False,
                reason=("開始年または終了年を特定できませんでした。"),
            )

        if resolution.start_year > resolution.end_year:
            return HistoricalPeriodResolution(
                label=resolution.label,
                resolved=False,
                reason=("開始年と終了年の関係が不正でした。"),
            )

        return resolution
