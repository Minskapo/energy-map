import streamlit as st
import pandas as pd
import plotly.express as px
import json

# 파일 경로
DATA_CSV = "한국전력거래소_지역별 시간별 태양광 및 풍력 발전량_20241231.csv"
GEOJSON_FILE = "korea_sido_boundaries.geojson"

# 지역명 정규화
region_mapping = {
    "서울시": "서울특별시",
    "부산시": "부산광역시",
    "대구시": "대구광역시",
    "인천시": "인천광역시",
    "광주시": "광주광역시",
    "대전시": "대전광역시",
    "울산시": "울산광역시",
    "세종시": "세종특별자치시",
    "제주": "제주특별자치도",
    "제주도": "제주특별자치도"
}

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_CSV, encoding="cp949")
    df["시간"] = pd.to_datetime(df["거래일자"]) + pd.to_timedelta(df["거래시간"] - 1, unit="h")
    df["월"] = df["시간"].dt.month
    df["일"] = df["시간"].dt.day
    df["시"] = df["시간"].dt.hour
    df = df[~df["지역"].isin(["육지"])]
    df["지역"] = df["지역"].replace(region_mapping)
    return df

@st.cache_data
def load_geojson():
    with open(GEOJSON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    st.set_page_config(layout="wide")
    st.title("🌞 2024 시도별 재생에너지 발전량 히트맵")

    df = load_data()
    geojson = load_geojson()

    # 지역 전체 목록 확보
    all_regions = pd.DataFrame({"지역": sorted(df["지역"].unique())})

    # 사용자 입력
    col1, col2, col3 = st.columns(3)
    with col1:
        month_options = sorted(df["월"].unique())
        month_selected = st.selectbox("월 선택", ["합계"] + [str(m) for m in month_options])
    with col2:
        if month_selected == "합계":
            day_selected = "합계"
        else:
            selected_month = int(month_selected)
            day_options = sorted(df[df["월"] == selected_month]["일"].unique())
            day_selected = st.selectbox("일 선택", ["합계"] + [str(d) for d in day_options])
    with col3:
        if month_selected == "합계" or day_selected == "합계":
            hour_selected = "합계"
        else:
            selected_day = int(day_selected)
            hour_options = sorted(df[(df["월"] == selected_month) & (df["일"] == selected_day)]["시"].unique())
            hour_selected = st.selectbox("시 선택", ["합계"] + [str(h) for h in hour_options])

    source_selected = st.radio("발전원 선택", ["태양광", "풍력", "합계"], horizontal=True)

    # 데이터 필터링
    dff = df.copy()
    if month_selected != "합계":
        dff = dff[dff["월"] == int(month_selected)]
    if day_selected != "합계":
        dff = dff[dff["일"] == int(day_selected)]
    if hour_selected != "합계":
        dff = dff[dff["시"] == int(hour_selected)]

    if source_selected != "합계":
        dff = dff[dff["연료원"] == source_selected]

    # ---------------- 히트맵 ----------------
    df_map = dff.groupby("지역")["전력거래량(MWh)"].sum().reset_index()
    df_map = pd.merge(all_regions, df_map, on="지역", how="left").fillna(0)

    fig_map = px.choropleth(
        df_map,
        geojson=geojson,
        locations="지역",
        featureidkey="properties.CTP_KOR_NM",
        color="전력거래량(MWh)",
        color_continuous_scale="YlOrRd",
        range_color=(0, df_map["전력거래량(MWh)"].max()),
        labels={"전력거래량(MWh)": "발전량(MWh)", "지역": "시도"},
        title="🗺 시도별 발전량 히트맵"
    )
    fig_map.update_geos(fitbounds="locations", visible=False)
    st.plotly_chart(fig_map, use_container_width=True)

    # ---------------- 라인차트 ----------------
    df_line = dff.groupby(["시간", "지역"])["전력거래량(MWh)"].sum().reset_index()
    fig_line = px.line(
        df_line,
        x="시간",
        y="전력거래량(MWh)",
        color="지역",
        title="📈 시간대별 시도별 발전량 추이",
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # ---------------- 애니메이션 ----------------
    if hour_selected == "합계":
        st.subheader("⏱ 시간대별 발전량 애니메이션")

        df_anim = dff.groupby(["시", "지역"])["전력거래량(MWh)"].sum().reset_index()
        df_anim = pd.merge(all_regions, df_anim, on="지역", how="right").fillna(0)

        fig_anim = px.choropleth(
            df_anim,
            geojson=geojson,
            locations="지역",
            featureidkey="properties.CTP_KOR_NM",
            color="전력거래량(MWh)",
            animation_frame="시",
            color_continuous_scale="YlOrRd",
            range_color=(0, df_anim["전력거래량(MWh)"].max()),
            labels={"전력거래량(MWh)": "발전량(MWh)", "지역": "시도"},
        )
        fig_anim.update_geos(fitbounds="locations", visible=False)
        st.plotly_chart(fig_anim, use_container_width=True)

if __name__ == "__main__":
    main()