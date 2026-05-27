# AI 댐 관리 대시보드 공유용 실행 방법

## 1. 이 폴더의 목적

이 폴더는 실시간 MySQL DB와 API 인증키 없이 실행할 수 있는 공유용 Streamlit 대시보드입니다.  
현재까지 로컬 DB에 쌓인 데이터를 CSV 스냅샷으로 변환하여 `data` 폴더에 넣었습니다.

따라서 팀원이나 발표 환경에서는 `.env`, MySQL, 공공데이터포털 인증키 없이도 화면을 확인할 수 있습니다.

## 2. 실행 방법

터미널에서 이 폴더로 이동한 뒤 실행합니다.

```bash
cd 공유용_Streamlit_대시보드
pip install -r requirements.txt
streamlit run app.py
```

실행 후 브라우저에 표시되는 주소로 접속하면 됩니다. 보통 아래 주소입니다.

```text
http://localhost:8501
```

## 3. 포함된 데이터

`data` 폴더에는 다음 CSV가 들어 있습니다.

| 파일 | 내용 |
|---|---|
| `latest_summary.csv` | 20개 댐 최신 수문값과 3시간 뒤 예측 결과 |
| `observation_history_72h.csv` | 최근 72시간 수문 운영 이력 |
| `weather_forecast_latest.csv` | 최신 기상청 초단기/단기 예보 스냅샷 |
| `prediction_validation.csv` | 3시간 뒤 예측값과 실제값 검증 결과 |
| `downstream_representative.csv` | 대표 하류 수위관측소 및 최신 수위/유량 |
| `downstream_candidates.csv` | 하류 수위관측소 후보 |
| `five_day_range.csv` | 1~5일 장기 누적 방류 범위 예측 결과 |
| `twostage_detail.csv` | Two-Stage 방류 변화량 실험 상세 지표 |
| `twostage_grade.csv` | 댐별 예측 활용 등급 |

## 4. 공유할 때 주의사항

- `.env` 파일은 공유하지 않습니다.
- 공공데이터포털 인증키는 GitHub에 올리지 않습니다.
- MySQL 비밀번호도 공유하지 않습니다.
- 이 공유용 버전은 실시간 자동수집이 아니라 CSV 스냅샷 기준입니다.
- 실시간 자동수집/예측은 로컬 실험버전에서만 실행됩니다.

## 5. GitHub에 올리는 방법

프로젝트 전체가 아니라 이 폴더만 따로 올리는 것이 안전합니다.

1. GitHub에서 새 저장소 생성
2. 이 `공유용_Streamlit_대시보드` 폴더 내용을 업로드
3. `app.py`, `requirements.txt`, `README_공유방법.md`, `data` 폴더가 포함되어 있는지 확인
4. `.env`가 없는지 확인

## 6. Streamlit Community Cloud 배포 방법

1. GitHub에 공유용 폴더 내용을 올립니다.
2. [Streamlit Community Cloud](https://streamlit.io/cloud)에 로그인합니다.
3. `New app`을 누릅니다.
4. GitHub 저장소를 선택합니다.
5. Main file path를 `app.py`로 설정합니다.
6. Deploy를 누릅니다.

배포 후 생성되는 URL을 팀원이나 교수님에게 공유하면 됩니다.

## 7. 발표 시 설명 문장

> 공유용 대시보드는 실시간 API 키와 DB 연결 없이 실행할 수 있도록, 로컬에서 수집한 최신 수문 운영 정보, 기상예보, 하류 수위, 예측 결과를 CSV 스냅샷으로 저장한 버전입니다. 실제 운영 버전은 30분마다 API를 수집하고 DB에 저장하지만, 공유용 버전은 동일한 화면을 재현하기 위한 시연용입니다.
