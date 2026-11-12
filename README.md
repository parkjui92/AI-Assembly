# AI-Assembly

국회사무처 의정연수원 신임관리자 과정 · 생성형 AI 업무 활용(심화): Claude Code
**법률안 검토보고서 에이전트 설계 및 업무 자동화** · 2026. 10. 26.

**바로 열기: [강의자료(HTML)](https://parkjui92.github.io/AI-Assembly/slides/) · [입법조사관용 MCP·API 도구 모음(HTML)](https://parkjui92.github.io/AI-Assembly/tools/)**

## 1. 강의자료

| 형식 | 바로 보기 | 내려받기 | 비고 |
|---|---|---|---|
| HTML | [브라우저에서 열기](https://parkjui92.github.io/AI-Assembly/slides/) | [slides/index.html](slides/index.html) 화면의 ⤓(Download raw file) | 클릭·←→로 넘김, 복사 버튼 작동 |
| PDF | [브라우저에서 열기](https://parkjui92.github.io/AI-Assembly/slides/강의자료_법률안검토보고서에이전트_20261026.pdf) | [PDF 내려받기](https://github.com/parkjui92/AI-Assembly/raw/main/slides/강의자료_법률안검토보고서에이전트_20261026.pdf) | 정지 화면, 글꼴 내장 |

## 2. 입법조사관용 MCP·API 도구 모음

Claude Code에 붙여 쓰는 법령·의안·입법례·재정·통계 자료원과 연결 방법(2026. 10. 26. 기준)

| 형식 | 바로 보기 | 내려받기 |
|---|---|---|
| HTML | [브라우저에서 열기](https://parkjui92.github.io/AI-Assembly/tools/) | [tools/index.html](tools/index.html) 화면의 ⤓(Download raw file) |
| PDF | [브라우저에서 열기](https://parkjui92.github.io/AI-Assembly/tools/입법조사관_MCP_API_도구모음.pdf) | [PDF 내려받기](https://github.com/parkjui92/AI-Assembly/raw/main/tools/입법조사관_MCP_API_도구모음.pdf) |
| 원고(md) | [tools/입법조사관_MCP_API_도구모음.md](tools/입법조사관_MCP_API_도구모음.md) | 같은 화면의 ⤓ |

## 3. 플러그인: 법률안 검토보고서 작성팀(bill-review)

검토설계 → 관문①(설계 판정) → 쟁점 승인 → 자료조사·조문 원장 → 집필 → 조문 대조 검문소 → 관문②(초안 검수) → 한글(.hwpx) 변환

**플러그인 저장소: [plugins/bill-review](https://github.com/parkjui92/AI-Assembly/tree/main/plugins/bill-review)** (에이전트 5 · 스킬 8 · 조문 대조 검문소 스크립트, MIT)

```bash
claude plugin marketplace add parkjui92/AI-Assembly
claude plugin install bill-review@ai-assembly
```

- 설치 뒤 Claude 앱을 다시 시작하고, 같은 작업 폴더에서 "법률안 검토보고서 작성팀의 팀원과 스킬을 표로 보여줘"로 확인
- 법령 현행 확인에는 [korean-law-mcp](https://github.com/chrisryugj/korean-law-mcp), 한글 문서 읽기·변환에는 [kordoc](https://github.com/chrisryugj/kordoc) 연결 권장
- 인증키(국가법령정보 OC 등)는 채팅창이 아니라 작업 폴더의 `.env`에 보관

## 4. 실습 법률안 받기

실습 자료는 따로 나눠 드리지 않습니다. 작업 폴더(`법률안실습`)를 만든 뒤 Claude Code에 요청해 의안정보시스템에서 직접 받습니다.

| 자료 | 언제 | 주소 |
|---|---|---|
| 의안원문(자전거법 일부개정안 2117808) | 해보기 ① · `입력/`에 저장 | [PDF](https://likms.assembly.go.kr/filegate/servlet/FileGate?bookId=51621BDE-4DCB-C7F4-932C-E5C192D431F9&type=1) |
| 실제 검토보고서(행정안전위원회) | 해보기 ⑬ · 초안 저장 뒤 `비교자료/`에 저장 | [PDF](https://likms.assembly.go.kr/filegate/servlet/FileGate?bookId=64187374-C2BC-8199-5B83-F437B744CE78&type=1) |

## 5. 공공AX 참고 사례

- [모두의 공공AX 사례 아카이브](https://hollobit.github.io/PAX/) — Threads와 오픈채팅에서 수집한 공공기관 AI 전환(AX) 사례 모음(hollobit)

## 유의

- 초안은 에이전트가, 쟁점 판단과 결론은 작성자가 함
- 비공개 자료·내부 회답·개인정보는 반입 기준을 확인한 뒤 넣음
- 강의자료 출처는 각 슬라이드 아래 줄에 표기

문의: 박주이 · 한양대학교 과학기술정책연구소 · parkjui92@gmail.com
라이선스: 플러그인 MIT(`plugins/bill-review/LICENSE`)
