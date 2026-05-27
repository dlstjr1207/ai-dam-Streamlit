from __future__ import annotations

from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

st.set_page_config(page_title="AI 댐 관리 대시보드 공유용", layout="wide", initial_sidebar_state="expanded")


@st.cache_data
def read_csv(name: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", parse_dates=parse_dates or [])


def fmt_num(value, unit: str = "", digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "-"
    try:
        return f"{float(value):,.{digits}f}{unit}"
    except (TypeError, ValueError):
        return "-"


def fmt_dt(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return pd.to_datetime(value).strftime("%Y-%m-%d %H:%M")


def card(title: str, value: str, caption: str = "", color: str = "#2563eb") -> None:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left-color:{color};">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, caption: str = "") -> None:
    st.markdown(f"### {title}")
    if caption:
        st.caption(caption)


def review_text(value) -> str:
    mapping = {
        "불필요": "현재 방류 유지",
        "관찰": "주의 관찰",
        "관찰 필요": "주의 관찰",
        "검토 필요": "방류 조정 검토",
        "데이터부족": "예측 보류",
        "데이터 부족": "예측 보류",
    }
    if value is None or pd.isna(value):
        return "예측 보류"
    return mapping.get(str(value), str(value))


def status_info(row: pd.Series) -> tuple[str, str, str, list[int]]:
    level = row.get("discharge_change_level")
    if pd.isna(row.get("predicted_discharge_3h")):
        return "예측 보류", "예측 입력값 확인 필요", "#64748b", [100, 116, 139, 170]
    if level == "높음":
        return "방류 조정 검토", "3시간 뒤 방류 변화 가능성 높음", "#dc2626", [220, 38, 38, 190]
    if level == "보통":
        return "주의 관찰", "3시간 뒤 방류 변화 가능성 보통", "#d97706", [217, 119, 6, 185]
    return "현재 방류 유지", "3시간 뒤 방류 변화 가능성 낮음", "#16a34a", [22, 163, 74, 175]


def add_validation_metrics(validation: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    if validation.empty:
        return validation
    thresholds = {}
    for dam_code, group in history.groupby("dam_code"):
        discharge = pd.to_numeric(group["totdcwtrqy"], errors="coerce").dropna()
        if discharge.empty:
            thresholds[int(dam_code)] = 1.0
            continue
        mean_based = discharge.mean() * 0.05
        volatility_based = discharge.diff().abs().std() * 0.5
        thresholds[int(dam_code)] = round(float(max(1.0, mean_based, 0 if pd.isna(volatility_based) else volatility_based)), 2)

    result = validation.copy()
    result["유입량 절대오차"] = (result["predicted_inflow_3h"] - result["actual_inflow_3h"]).abs()
    result["방류량 절대오차"] = (result["predicted_discharge_3h"] - result["actual_discharge_3h"]).abs()
    result["댐별 변화기준"] = result["dam_code"].map(lambda code: thresholds.get(int(code), 1.0))
    result["실제 방류변화"] = (result["actual_discharge_3h"] - result["base_discharge"]).abs() >= result["댐별 변화기준"]
    result["예측 변화신호"] = result["discharge_change_level"].isin(["보통", "높음"])
    result["변화신호 적중"] = result["실제 방류변화"] == result["예측 변화신호"]
    return result


def daily_weather_summary(weather: pd.DataFrame) -> pd.DataFrame:
    if weather.empty:
        return pd.DataFrame()
    data = weather.copy()
    data["forecast_datetime"] = pd.to_datetime(data["forecast_datetime"], errors="coerce")
    data["rain"] = pd.to_numeric(data.get("rain"), errors="coerce").fillna(0)
    data["date"] = data["forecast_datetime"].dt.date
    return (
        data.groupby("date", as_index=False)
        .agg(예상강수량_mm=("rain", "sum"), 최저기온=("tmp", "min"), 최고기온=("tmp", "max"))
        .rename(columns={"date": "날짜"})
    )


summary = read_csv("latest_summary.csv", parse_dates=["obsrdt", "pred_base_time", "pred_target_time"])
history = read_csv("observation_history_72h.csv", parse_dates=["obsrdt"])
weather = read_csv("weather_forecast_latest.csv", parse_dates=["base_datetime", "forecast_datetime"])
validation = read_csv("prediction_validation.csv", parse_dates=["pred_base_time", "pred_target_time"])
downstream = read_csv("downstream_representative.csv", parse_dates=["observed_at"])
downstream_candidates = read_csv("downstream_candidates.csv")
five_day = read_csv("five_day_range.csv")
twostage_grade = read_csv("twostage_grade.csv")

validation = add_validation_metrics(validation, history)

if summary.empty:
    st.error("공유용 CSV 데이터가 없습니다. data 폴더를 확인하세요.")
    st.stop()

st.markdown(
    """
    <style>
    .main { background:#f4f7fb; }
    .metric-card {
        background:#fff;
        border:1px solid #d8e0ea;
        border-left:4px solid #2563eb;
        border-radius:8px;
        padding:14px 16px;
        min-height:104px;
        box-shadow:0 1px 2px rgba(15,23,42,.04);
    }
    .metric-title { color:#52647a; font-size:.88rem; font-weight:700; margin-bottom:8px; }
    .metric-value { color:#071225; font-size:1.5rem; font-weight:850; line-height:1.25; }
    .metric-caption { color:#66758a; font-size:.82rem; margin-top:6px; }
    .notice {
        border:1px solid #bfdbfe;
        background:#eff6ff;
        color:#1e3a8a;
        border-radius:8px;
        padding:12px 14px;
        margin:10px 0 14px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.title("AI 댐 관리")
    st.caption("공유용 CSV 스냅샷 대시보드입니다. 실시간 DB/API 없이 실행됩니다.")
    dam_names = summary["dam_name"].dropna().tolist()
    selected_name = st.selectbox("댐 선택", dam_names, index=dam_names.index("남강") if "남강" in dam_names else 0)
    st.divider()
    latest_obs = summary["obsrdt"].max()
    st.caption(f"스냅샷 기준: {fmt_dt(latest_obs)}")
    st.caption("김천부항댐 제외 20개 다목적댐 기준")

selected = summary[summary["dam_name"] == selected_name].iloc[0]
selected_code = int(selected["dam_code"])
selected_history = history[history["dam_code"] == selected_code].copy()
selected_weather = weather[weather["dam_code"] == selected_code].copy()
selected_validation = validation[validation["dam_code"] == selected_code].copy()
selected_downstream = downstream[downstream["dam_code"] == selected_code].copy()
selected_candidates = downstream_candidates[downstream_candidates["dam_code"] == selected_code].head(3).copy()
status_label, status_reason, status_color, status_rgba = status_info(selected)

st.title("AI 댐 관리 대시보드")
st.caption("실시간 수문 운영 정보, 기상예보, 하류 수위, 3시간 뒤 예측 결과를 CSV 스냅샷으로 재현한 공유용 대시보드")

top = st.columns(4)
with top[0]:
    card("현재 시각", fmt_dt(pd.Timestamp.now()), "대시보드 표시 시각")
with top[1]:
    card("최신 수문 관측", fmt_dt(selected.get("obsrdt")), "수문 운영 정보")
with top[2]:
    card("최신 예측 기준", fmt_dt(selected.get("pred_base_time")), "3시간 뒤 예측")
with top[3]:
    card("3시간 뒤 목표시각", fmt_dt(selected.get("pred_target_time")), "예측 대상")

section(f"{selected_name}댐 상세 현황", "현재 수문값과 3시간 뒤 예측 결과입니다.")
detail = st.columns(6)
with detail[0]:
    card("현재 유입량", fmt_num(selected.get("inflowqy"), " ㎥/s"), "수문 관측값", "#0284c7")
with detail[1]:
    card("현재 방류량", fmt_num(selected.get("totdcwtrqy"), " ㎥/s"), "수문 관측값", "#0284c7")
with detail[2]:
    card("저수율", fmt_num(selected.get("rsvwtrt"), "%"), "현재 저수 상태", "#16a34a")
with detail[3]:
    card("수위", fmt_num(selected.get("lowlevel"), " m"), "현재 수위", "#16a34a")
with detail[4]:
    card("3시간 뒤 유입량", fmt_num(selected.get("predicted_inflow_3h"), " ㎥/s"), "모델 예측", "#d97706")
with detail[5]:
    card("3시간 뒤 방류량", fmt_num(selected.get("predicted_discharge_3h"), " ㎥/s"), "운영 참고값", "#d97706")

tab_summary, tab_weather, tab_operation, tab_prediction, tab_validation, tab_downstream, tab_map, tab_five = st.tabs(
    ["요약", "기상예보", "수문 운영 정보", "3시간 뒤 방류 판단", "실시간 검증", "하류 수위", "지도", "5일 예측 해석"]
)

with tab_summary:
    left, right = st.columns([1.1, 1])
    with left:
        section("최근 72시간 변화", "유입량, 방류량, 저수율 추세")
        if selected_history.empty:
            st.info("이 댐의 72시간 이력이 없습니다.")
        else:
            chart = selected_history.set_index("obsrdt")[["inflowqy", "totdcwtrqy", "rsvwtrt"]]
            st.line_chart(chart, height=320)
    with right:
        section("판단 요약", "실제 방류 명령이 아닌 운영 판단 보조 지표입니다.")
        card("3시간 뒤 조치", status_label, status_reason, status_color)
        st.markdown(
            f"""
            <div class="notice">
            현재 방류량 {fmt_num(selected.get("totdcwtrqy"), " ㎥/s")} 기준,
            3시간 뒤 예상 방류량은 {fmt_num(selected.get("predicted_discharge_3h"), " ㎥/s")}입니다.
            이 값은 자동 방류 명령이 아니라 관리자 판단 보조값입니다.
            </div>
            """,
            unsafe_allow_html=True,
        )

with tab_weather:
    section("기상예보", "댐 좌표 격자와 연결된 초단기/단기 예보 스냅샷")
    daily = daily_weather_summary(selected_weather)
    if not daily.empty:
        st.bar_chart(daily.set_index("날짜")[["예상강수량_mm"]], height=240)
        st.dataframe(daily, use_container_width=True, hide_index=True)
    st.dataframe(selected_weather, use_container_width=True, hide_index=True, height=360)

with tab_operation:
    section("현재 수문 운영 정보", "가장 최근 수문 관측값")
    operation = summary[
        ["dam_name", "dam_code", "obsrdt", "inflowqy", "lowlevel", "rf", "rsvwtqy", "rsvwtrt", "totdcwtrqy"]
    ].rename(
        columns={
            "dam_name": "댐 이름",
            "dam_code": "댐 코드",
            "obsrdt": "관측시각",
            "inflowqy": "유입량",
            "lowlevel": "수위",
            "rf": "강수량",
            "rsvwtqy": "저수량",
            "rsvwtrt": "저수율",
            "totdcwtrqy": "방류량",
        }
    )
    st.dataframe(operation, use_container_width=True, hide_index=True)

with tab_prediction:
    section("3시간 뒤 방류 판단", "방류량 직접 명령이 아니라 방류 변화 가능성 판단입니다.")
    cols = st.columns(3)
    with cols[0]:
        card("운영 판단", status_label, status_reason, status_color)
    with cols[1]:
        card("예상 방류량", fmt_num(selected.get("predicted_discharge_3h"), " ㎥/s"), "3시간 뒤 참고값")
    with cols[2]:
        card("관리자 안내", review_text(selected.get("release_review")), "모델 판단 문구")
    comparison = summary[
        ["dam_name", "dam_code", "obsrdt", "totdcwtrqy", "pred_target_time", "predicted_discharge_3h", "discharge_change_level", "release_review"]
    ].copy()
    statuses = comparison.apply(status_info, axis=1, result_type="expand")
    comparison.insert(1, "3시간 뒤 조치", statuses[0])
    comparison["release_review"] = comparison["release_review"].apply(review_text)
    st.dataframe(comparison.rename(columns={
        "dam_name": "댐 이름", "dam_code": "댐 코드", "obsrdt": "관측시각", "totdcwtrqy": "현재 방류량",
        "pred_target_time": "예측 목표시각", "predicted_discharge_3h": "예상 방류량",
        "discharge_change_level": "변화 신호", "release_review": "관리자 안내"
    }), use_container_width=True, hide_index=True, height=420)

with tab_validation:
    section("실시간 예측 검증", "예측 목표시각의 실제 수문값과 매칭된 결과")
    if validation.empty:
        st.info("검증 데이터가 없습니다.")
    else:
        cols = st.columns(3)
        with cols[0]:
            card("검증 건수", f"{len(validation):,}건", "전체 댐 기준")
        with cols[1]:
            card("방류량 MAE", fmt_num(validation["방류량 절대오차"].mean(), " ㎥/s"), "낮을수록 좋음")
        with cols[2]:
            card("변화신호 적중률", fmt_num(validation["변화신호 적중"].mean() * 100, "%"), "댐별 변화 기준")
        show = selected_validation[
            ["dam_name", "pred_base_time", "pred_target_time", "base_discharge", "댐별 변화기준", "predicted_discharge_3h", "actual_discharge_3h", "방류량 절대오차", "실제 방류변화", "discharge_change_level", "변화신호 적중"]
        ].rename(columns={
            "dam_name": "댐 이름", "pred_base_time": "예측 기준", "pred_target_time": "검증 시각",
            "base_discharge": "기준 방류량", "predicted_discharge_3h": "예측 방류량",
            "actual_discharge_3h": "실제 방류량", "discharge_change_level": "변화 가능성"
        })
        st.dataframe(show, use_container_width=True, hide_index=True, height=360)

with tab_downstream:
    section("대표 하류 수위관측소", "방류 판단 보조를 위한 대표 하류/인접 수위관측소")
    if selected_downstream.empty:
        st.info("대표 하류 수위관측소 데이터가 없습니다.")
    else:
        ds = selected_downstream.iloc[0]
        cols = st.columns(4)
        with cols[0]:
            card("대표 관측소", str(ds.get("station_name")), f"코드 {ds.get('station_code')}")
        with cols[1]:
            card("댐과 거리", fmt_num(ds.get("distance_km"), " km"), "좌표 기준 직선거리")
        with cols[2]:
            card("최근 하류 수위", fmt_num(ds.get("water_level"), " m"), fmt_dt(ds.get("observed_at")))
        with cols[3]:
            card("최근 하류 유량", fmt_num(ds.get("flow_rate"), " ㎥/s"), "시자료 API 스냅샷")
        st.markdown(f'<div class="notice">선정 기준: {ds.get("selection_reason", "-")}</div>', unsafe_allow_html=True)
        with st.expander("후보 관측소 보기", expanded=False):
            st.dataframe(selected_candidates.fillna("-"), use_container_width=True, hide_index=True)

with tab_map:
    section("20개 댐 위치", "색상은 3시간 뒤 방류 조치 단계를 의미합니다.")
    map_df = summary.copy()
    info = map_df.apply(status_info, axis=1, result_type="expand")
    map_df["status_label"] = info[0]
    map_df["color"] = info[3]
    st.pydeck_chart(
        pdk.Deck(
            initial_view_state=pdk.ViewState(latitude=36.15, longitude=127.9, zoom=6.2, pitch=0),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=map_df,
                    get_position="[longitude, latitude]",
                    get_radius=13000,
                    get_fill_color="color",
                    pickable=True,
                )
            ],
            tooltip={"text": "{dam_name}댐\\n3시간 뒤 조치: {status_label}\\n현재 방류량: {totdcwtrqy}\\n예상 방류량: {predicted_discharge_3h}"},
        )
    )

with tab_five:
    section("5일 예측 해석", "장기 예측은 정확한 방류량보다 누적 강수와 방류 증가 가능성을 참고합니다.")
    if five_day.empty:
        st.info("5일 예측 결과 CSV가 없습니다.")
    else:
        part = five_day[five_day["댐이름"] == selected_name].copy() if "댐이름" in five_day.columns else pd.DataFrame()
        if part.empty:
            st.info("선택 댐의 5일 예측 해석이 없습니다.")
        else:
            cols = [col for col in ["예측구간", "예상강수량", "예상누적방류_하한", "예상누적방류_중앙", "예상누적방류_상한", "방류증가가능성", "운영판단", "운영해석"] if col in part.columns]
            st.dataframe(part[cols], use_container_width=True, hide_index=True)

st.caption("공유용 버전은 DB/API를 직접 호출하지 않고 CSV 스냅샷만 사용합니다. 실시간 운영 버전은 로컬 프로젝트의 실험용 대시보드에서 실행합니다.")
