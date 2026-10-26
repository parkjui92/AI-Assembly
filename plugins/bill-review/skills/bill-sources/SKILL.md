---
name: bill-sources
description: "법률안 검토에 쓰는 공개 자료원과 조회법. 국가법령정보(korean-law MCP — 현행·과거 시점 조문, 연혁, 판례·헌재 결정·법제처 해석례), 열린국회정보 의안 API(키 없이 브라우저 UA로 의안번호·법률안명 조회 — 제안일·회부일·상정일·처리 결과·유사 법률안), 의안정보시스템(의안원문·검토보고서 파일), 국내외 입법례(국회법률도서관·세계법제정보센터), 통계·연구자료(KOSIS·국회입법조사처·국회예산정책처 비용추계·PRISM)와, 공개 창구로 구할 수 없어 부처·이해관계자에게 받아야 하는 것의 경계를 담는다. 기준 시점 정하는 법과 가림 조건도 여기 있다. 자료조사관이 근거를 모을 때, 설계자가 의안 정보·기준 시점·조문 원장 목록을 정할 때 읽는다. '조문 현행 확인', '의안 정보 조회', '유사 법률안 찾아줘', '입법례 어디서', '판례 찾아줘' 요청에도 사용."
---

# 법률안 검토 자료원 — 어디서, 어떻게, 무엇은 못 구하나

교재(「법률안검토 표준교재」 p.44~54)가 꼽은 자료원을 Claude Code에서 부르는 방법으로 옮겼다. 경로는 2026-10-20 실측이다.

> **기억으로 조문을 쓰지 않는다.** 모델이 아는 법령은 배운 시점의 법령이고, 웹에는 옛 조문이 남아 있다.
> 조문은 부를 때마다 그날(또는 기준일) 원문을 받는다. 받은 원문은 `03b_조문원장/`에 그대로 둔다(`article-check`).

## 0. 인증키 — 작업 폴더의 `.env`
```
LAW_OC=...           # 국가법령정보 공동활용 인증값(open.law.go.kr 신청, 이메일 ID) — korean-law MCP를 쓰면 MCP 설정에 넣는다
ASSEMBLY_KEY=...     # 열린국회정보(open.assembly.go.kr) — 없으면 키 없이 5건씩
```
- **키를 채팅창에 붙여 넣지 않는다.** 대화 기록에 남는다. 붙여 넣었으면 `.env`로 옮기고 재발급을 권한다
- `.env`는 git에 올리지 않는다. 명령·장부·응답에 키 값을 적지 않는다(URL의 키 자리는 `KEY=〔키〕`)

## 1. 국가법령정보 — 조문은 원문으로

**korean-law MCP**(제3자 오픈소스 `chrisryugj/korean-law-mcp`, 법제처 Open API 기반)를 연결했으면 이것으로 한다.

| 하려는 일 | 도구 |
|---|---|
| 법령 찾기·MST 얻기, 시행예정 개정 확인 | `search_law(query="자전거 이용 활성화에 관한 법률")` — 결과에 `[현행]`·공포일·시행일, 시행예정 개정 안내가 붙는다 |
| 조문 원문(현행) | `get_law_text(mst=…, jo="제22조")` — `efYd` 없이 |
| **조문 원문(기준일)** | `get_law_text(mst=…, jo="제22조", efYd="20230216")` — 그날 시행 중이던 판을 준다(응답 첫 줄에 어느 판인지 적힌다) |
| 두 시점 비교·개정 연혁 | `legal_research(task="amendment_track", query=…, scenario="time_travel", fromDate=…, toDate=…)` |
| 판례·헌재 결정·해석례 | `search_decisions(domain="precedent"·"constitutional"·"interpretation", query=…)` → `get_decision_text` |
| 그 밖(조약·행정규칙·자치법규 등) | `discover_tools(intent=…)` → `execute_tool` |

- 도구 이름은 설치 방식에 따라 `mcp__plugin_korean-law_korean-law__get_law_text` 또는 `mcp__korean-law__get_law_text`로 보인다
- MCP가 없으면: `https://www.law.go.kr/DRF/lawService.do?OC=${LAW_OC}&target=law&MST={일련번호}&type=JSON` (인증값 필요). 웹 화면(`law.go.kr`)은 사람이 확인하는 용도로만
- **연결 안내(교육생)** — Claude Code에 "korean-law 플러그인 설치해줘"라고 하거나 `/plugin marketplace add chrisryugj/korean-law-mcp` → `/plugin install korean-law@korean-law-marketplace`. 설치 때 법제처 API 키(LAW_OC)를 묻는다

## 2. 열린국회정보 — 의안 정보 (키 없이 실습 가능)

`https://open.assembly.go.kr/portal/openapi/{서비스ID}?Type=json&pIndex=1&pSize=5&AGE=21&BILL_NO=2117808`
- **브라우저 사용자 에이전트를 붙인다** — `curl -s -A "Mozilla/5.0" "…"`. 붙이지 않으면 `Bad Request.`만 온다(2026-10-20 실측)
- **키가 없으면 한 번에 5건까지** 준다. 조건(`BILL_NO`·`BILL_NAME`·`AGE`)은 키 없이도 걸린다(실측: `BILL_NAME=자전거` → 전체 7건 중 5건). 더 받으려면 `pIndex`를 넘기거나 `KEY=${ASSEMBLY_KEY}`를 붙인다

| 서비스ID | 2026-10-20에 확인한 필드 | 쓰는 곳 |
|---|---|---|
| `ALLBILL` | `BILL_NO`·`BILL_NM`·`PPSR_NM`(제안자)·`PPSL_DT`(제안일)·`PPSL_SESS`(회기)·`JRCMIT_NM`(소관위)·`JRCMIT_CMMT_DT`(회부일)·`JRCMIT_PRSNT_DT`(상정일)·`JRCMIT_PROC_DT`·`RGS_RSLN_DT` | Ⅰ. 제안경위, **기준 시점(상정일)** |
| `nzmimeepazxkubdpn` | `BILL_ID`·`BILL_NO`·`BILL_NAME`·`COMMITTEE`·`PROPOSE_DT`·`PROC_RESULT`·`PROPOSER`·`DETAIL_LINK`·`MEMBER_LIST` | 의원 발의 법률안, **유사 법률안 목록**(`BILL_NAME=`), 의안 페이지 주소 |
| `TVBPMBILL11` | `BILL_NO`·`PROPOSER_KIND`·`CURR_COMMITTEE`·`COMMITTEE_DT`·`LINK_URL` | 회부 위원회·회부일 교차 확인 |
| `nwbpacrgavhjryiph` | `COMMITTEE_SUBMIT_DT`·`COMMITTEE_PRESENT_DT`·`PROC_RESULT_CD` | 위원회 상정일·처리 결과 |

- 의안 페이지(`DETAIL_LINK`, `likms.assembly.go.kr/bill/billDetail.do?billId=…`)는 스크립트로 그려지므로 **브라우저로 연다.** 의안원문·검토보고서·심사보고서 파일이 거기 있다. 파일 주소(`…/filegate/servlet/FileGate?bookId=…&type=0`)는 `curl -A "Mozilla/5.0" -L`로 받는다
- 받은 `.pdf`·`.hwp`는 `npx -y kordoc 파일 -o 파일.md`(또는 kordoc MCP `parse_document`)로 읽는다

## 3. 기준 시점 — 어느 날의 '현행'인가
| 상황 | 기준일 | 원장에 둘 것 |
|---|---|---|
| 계류 중인 법률안을 지금 검토 | 오늘 | 오늘 현행 |
| 지난 법률안으로 연습(실제 검토보고서와 비교) | **위원회 상정일**(`ALLBILL`의 `JRCMIT_PRSNT_DT`), 없으면 회부일 | 기준일 판 + 오늘 판(시점 차이 표시용) |
| 제안일과 기준일 사이에 대상 법률이 개정·공포됨 | 기준일 | 두 판 모두 — 개정안의 개정문이 바뀐 현행에 맞지 않을 수 있다(쟁점 후보) |

기준일 판과 오늘 판이 다른 것은 **오류가 아니라 시점 차이**다. 본문에 기준일을 밝힌다.

## 4. 유사 법률안과 지난 검토보고서 (교재 p.49)
- 같은 법률의 다른 개정안 — `nzmimeepazxkubdpn?BILL_NAME=(법률명 일부)`로 목록 → 의안 페이지에서 제안이유·검토보고서
- 의안정보시스템 "의안검색"의 **제안이유 및 주요내용 검색**·**심사보고서 본문 검색**(브라우저)
- 같은 취지가 다른 위원회에서 검토된 적이 있는지도 본다. 지난 검토보고서의 지적이 가장 직접적인 근거다

## 5. 입법례 (교재 p.50~52)
| 무엇 | 어디 |
|---|---|
| 국내 다른 법률의 같은 규정 | 국가법령정보(조문 내용 검색) · 국회법률정보시스템 `likms.assembly.go.kr/law` |
| 외국 법률 원문·번역 | 국회법률도서관 `law.nanet.go.kr` 외국법률번역DB · 최신외국입법정보, 법제처 세계법제정보센터 `world.moleg.go.kr` |
| 외국 제도 현황 | 국회입법조사처·국회도서관 보고서, 국책연구기관 보고서 |
- 외국 입법례는 **원문 법령명·조문과 번역 출처**를 함께 적는다. 언론·블로그로만 찾았으면 `〔2차〕`

## 6. 판례·헌재 결정·해석례 (교재 p.52~54)
- korean-law `search_decisions`(§1) → 본문은 `get_decision_text`. 사건번호·선고일·법원을 적는다
- 사람이 확인할 화면: 대법원 종합법률정보 `glaw.scourt.go.kr` · 헌법재판소 `isearch.ccourt.go.kr` · 법제처 법령해석 `lawmaking.go.kr`

## 7. 통계·연구자료 (교재 p.46~47, 54)
- 통계: 국가통계포털 `kosis.kr` · 국회예산정책처 재정경제통계 `nabostats.go.kr` · 부처 통계(기준연도를 적는다)
- 국회 소속기관: 국회입법조사처 보고서, **국회예산정책처 비용추계서**(재정이 드는 법률안), 국회도서관
- 정책연구용역: `prism.go.kr` · 학술: DBpia·KISS·국회전자도서관
- 연구자 사이 견해가 갈리면 한 편만 근거로 삼지 않는다

## 8. 공개 창구로 구할 수 없는 것 — 부처·이해관계자에게 받는다
- 소관부처 의견서, 부처 간 이견, 집행 실태·내부 통계, 정부안의 조문별 개정 이유서·법제처 심사자료
- 이익단체·전문가 의견(공청회 자료집은 공개 — 국회도서관 "국회의원 정책자료"), 국회입법예고시스템 `pal.assembly.go.kr`에 올라온 국민 의견
- 이 팀은 이것들을 **지어내지 않는다.** 장부 끝 `부처·이해관계자에게 받을 것` 목록으로 넘기고, 본문에는 `〔판단 필요: 소관부처 의견 — 의견 조회 후 기재〕` 자리만 둔다

## 9. 가림 조건 — 지난 법률안으로 연습할 때
- 그 법률안의 **검토보고서·심사보고서·위원회 회의록**은 정답지다. 대조표를 만들 때까지 열지 않는다
- 기준일 뒤에 나온 자료(그 뒤의 개정 이유·보도)는 근거로 쓰지 않는다. 기준일 뒤 현행 조문은 시점 차이를 적는 데만
- 검색 결과에 정답지가 나오면 건너뛰고, 장부에 "가림 조건으로 열지 않음"이라고 적는다
