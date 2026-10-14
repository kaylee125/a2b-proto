# 배포 운영 절차 (runlot)

배포 대상은 `site/` 폴더이고 설정은 루트의 `runlot.json`(`{ "name": "galatalkka", "assets": "site" }`)이다. 서버 코드는 없다(정적 사이트). 배경과 리스크는 `docs/deploy-plan-runlot.md`.

## 1. 배포 전 점검 (매번)
생성 데이터(`cache/`, `data/`, `site/data/`의 `rules.json` 외 파일)는 git에 없다. 새로 받았다면 README의 '실행' 순서(본인 API 키 필요)로 먼저 만든다. `data/complex_trades.json.gz`가 이미 있으면 아래 3개 명령(결과는 항상 같고 2분 내외)만 실행한다.
```
python3 build_data.py && python3 history.py && python3 area.py
```
```
python3 -m pytest -q                                   # 전부 통과해야 함(배포 제한 테스트 포함)
find site \( -name ".*" -o -type l \)                  # 숨김 파일·심볼릭 링크가 없어야 함(출력 없음)
grep -rIlE "serviceKey|SERVICE_KEY|api[_-]?key|secret|password" site   # 출력 없음
```
`test_runlot_config_and_bundle_limits`가 파일 수(≤16,000, runlot 한도 20,000의 80%), 압축 크기(<64MiB), 이름 규칙을 자동으로 확인한다.

## 2. 최초 배포
| 단계 | 명령 | 비고 |
|---|---|---|
| 가입 | `dash.runlot.io` | 조직 슬러그는 **변경 불가** |
| 설치 | `npm i -g runlot` | 이 환경은 npm 보안 검사(SCFW)가 켜져 있어 비대화형에서는 경고 시 차단될 수 있음 → 터미널에서 직접 실행 |
| 로그인 | `runlot login` → `runlot whoami` | 브라우저 로그인 |
| 미리보기 | `runlot deploy --preview beta` | 운영과 분리된 별도 주소 |
| 점검 | 아래 §4 점검표 | 문제 없을 때만 다음 단계 |
| 접근 | `runlot access set password` | 베타 기간. 기본 접근 모드는 문서에 없으니 `runlot access`로 먼저 확인 |
| 운영 | `runlot deploy` → `runlot versions` | 출력: `v1 galatalkka.<조직>.runlot.app` |

## 3. 롤백
```
runlot versions                 # * 표시가 현재 버전
runlot rollback <이전 버전>      # 확인 질문에 응답(CI는 -y). 새 빌드 없이 기존 버전을 다시 켬
```
버전은 삭제되지 않고 개수 제한이 없다. DB를 쓰지 않아 데이터 롤백 문제는 없다.

## 4. 미리보기·운영 점검표
- [ ] 홈·단지 상세·A↔B 비교·자금 계획·후보 찾기·관심 입지·설정 화면과 온보딩 가이드가 열린다
- [ ] 주소 직접 입력·새로고침: `…/#/c/<id>`, `…/#/find?loc=11350`
- [ ] 개발자도구 Network: 데이터 요청이 모두 `?v=` 를 달고 200, 응답 헤더 `Content-Type`·`Cache-Control`·압축 기록
- [ ] 없는 경로(`/nope`)의 응답 기록
- [ ] 비밀번호 모드에서도 데이터 요청이 정상
- [ ] 실제 폰(360px)·다크 모드·터치 확인

## 5. 월간 데이터 갱신 루틴 (수동)
```
python3 tools/fetch_history.py 201610 <전월YYYYMM> cache          # 서울 25구 + 구리·하남·남양주
python3 tools/fetch_history.py 201610 <전월YYYYMM> cache metro    # 수원·분당·동안·동탄
python3 tools/fetch_history.py 201610 <전월YYYYMM> cache uiwang   # 의왕
python3 tools/extract_trades.py && python3 build_data.py && python3 history.py && python3 area.py
sed -i '' 's/?v=\([0-9]*\)/?v=NEXT/g' site/index.html             # ?v= 를 올려야 사용자 브라우저가 새 데이터를 받음(NEXT 는 현재 값+1)
python3 -m pytest -q   # 고정 수치 테스트(단지 수·라벨 수 등)는 데이터가 바뀌면 의도적으로 갱신해야 함
runlot deploy
```
- 국토부 API 일일 한도(약 9,000회)가 키 하나에 걸려 있다. 429가 나면 하루 뒤 재시도(`fetch_history.py`가 자동으로 30분 간격 재시도). 다산동 일일 수집분(`data/dasan.db`)은 선택 입력이다.
- 추세 기준일은 "두 달 전 월말"이라 월 1회 갱신이 적당하다.

### 알려진 미해결 문제 (갱신 전 확인 필요, 아직 검증하지 않음)
- 구리·하남·다산은 2023-11 이후 거래를 `loop2_rows.json`·`dasan.db`에서 읽는데, `fetch_history.py`의 기본 세트(서울+구리·하남·남양주)로 신규 월을 받으면 같은 거래가 두 번 들어갈 수 있다(`extract_trades.py`에 중복 제거 없음). 갱신 후 **월별 거래 건수와 `test_area_trade_counts_match_raw_trades`**로 중복을 확인하고, 자동화 전에 중복 제거를 넣어야 한다.
- 위 고정 수치 테스트(`test_data.py`의 단지·라벨 개수)는 데이터가 바뀔 때마다 새 값으로 고쳐야 한다.
