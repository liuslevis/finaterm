from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Indicator:
    id: str
    name: str
    name_zh: str
    description: str
    category: str
    source_series_id: str
    frequency: str
    unit: str
    seasonal_adjustment: str
    source: str = "fred"
    status: str = "available"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _i(
    id: str,
    name: str,
    name_zh: str,
    category: str,
    series: str,
    frequency: str,
    unit: str,
    seasonal_adjustment: str = "seasonally adjusted",
    description: str = "",
) -> Indicator:
    return Indicator(
        id=id,
        name=name,
        name_zh=name_zh,
        description=description or name,
        category=category,
        source_series_id=series,
        frequency=frequency,
        unit=unit,
        seasonal_adjustment=seasonal_adjustment,
    )


INDICATORS = (
    _i("cpi", "Consumer Price Index", "消费者价格指数", "inflation", "CPIAUCSL", "monthly", "index"),
    _i("core_cpi", "Core Consumer Price Index", "核心消费者价格指数", "inflation", "CPILFESL", "monthly", "index"),
    _i("pce_price_index", "PCE Price Index", "PCE 价格指数", "inflation", "PCEPI", "monthly", "index"),
    _i("core_pce", "Core PCE Price Index", "核心 PCE 价格指数", "inflation", "PCEPILFE", "monthly", "index"),
    _i("ppi_final_demand", "PPI Final Demand", "最终需求生产者价格指数", "inflation", "PPIFIS", "monthly", "index"),
    _i("nonfarm_payrolls", "All Employees, Total Nonfarm", "非农就业人数", "employment", "PAYEMS", "monthly", "thousands"),
    _i("unemployment_rate", "Unemployment Rate", "失业率", "employment", "UNRATE", "monthly", "percent"),
    _i("average_hourly_earnings", "Average Hourly Earnings", "平均时薪", "employment", "CES0500000003", "monthly", "usd_per_hour"),
    _i("initial_jobless_claims", "Initial Jobless Claims", "首次申请失业救济人数", "employment", "ICSA", "weekly", "count"),
    _i("jolts_job_openings", "JOLTS Job Openings", "JOLTS 职位空缺", "employment", "JTSJOL", "monthly", "thousands"),
    _i("nominal_gdp", "Gross Domestic Product", "名义 GDP", "growth", "GDP", "quarterly", "billions_usd"),
    _i("real_gdp", "Real Gross Domestic Product", "实际 GDP", "growth", "GDPC1", "quarterly", "billions_chained_2017_usd"),
    _i("industrial_production", "Industrial Production Index", "工业生产指数", "growth", "INDPRO", "monthly", "index"),
    _i("retail_sales", "Advance Retail Sales", "零售销售", "consumption", "RSAFS", "monthly", "millions_usd"),
    _i("personal_income", "Personal Income", "个人收入", "consumption", "PI", "monthly", "billions_usd"),
    _i("personal_consumption", "Personal Consumption Expenditures", "个人消费支出", "consumption", "PCE", "monthly", "billions_usd"),
    _i("consumer_sentiment", "University of Michigan Consumer Sentiment", "密歇根消费者信心", "consumption", "UMCSENT", "monthly", "index"),
    _i("housing_starts", "Housing Starts", "新屋开工", "housing", "HOUST", "monthly", "thousands"),
    _i("building_permits", "Building Permits", "营建许可", "housing", "PERMIT", "monthly", "thousands"),
    _i("new_home_sales", "New One Family Houses Sold", "新屋销售", "housing", "HSN1F", "monthly", "thousands"),
    _i("existing_home_sales", "Existing Home Sales", "成屋销售", "housing", "EXHOSLUSM495S", "monthly", "millions"),
    _i("case_shiller_home_price", "S&P CoreLogic Case-Shiller U.S. National Home Price Index", "Case-Shiller 房价指数", "housing", "CSUSHPINSA", "monthly", "index", "not seasonally adjusted"),
    _i("trade_balance", "U.S. Trade Balance: Goods and Services", "美国商品与服务贸易差额", "trade", "BOPGSTB", "monthly", "millions_usd"),
    _i("business_inventories", "Business Inventories", "商业库存", "inventories", "BUSINV", "monthly", "millions_usd"),
    _i("fed_funds_rate", "Effective Federal Funds Rate", "有效联邦基金利率", "rates", "FEDFUNDS", "monthly", "percent", "not seasonally adjusted"),
    _i("treasury_2y", "2-Year Treasury Yield", "两年期美国国债收益率", "rates", "DGS2", "daily", "percent", "not seasonally adjusted"),
    _i("treasury_10y", "10-Year Treasury Yield", "十年期美国国债收益率", "rates", "DGS10", "daily", "percent", "not seasonally adjusted"),
    _i("treasury_10y_2y_spread", "10-Year Minus 2-Year Treasury Spread", "十年期减两年期国债利差", "rates", "T10Y2Y", "daily", "percentage_points", "not seasonally adjusted"),
)

INDICATOR_BY_ID = {indicator.id: indicator for indicator in INDICATORS}

