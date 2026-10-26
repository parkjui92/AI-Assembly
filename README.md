# AI-Assembly

국회사무처 의정연수원 신임관리자 과정 · 생성형 AI 업무 활용(심화): Claude Code
**법률안 검토보고서 에이전트 설계 및 업무 자동화** · 2026. 10. 26.

**바로 열기: [강의자료(HTML)](https://parkjui92.github.io/AI-Assembly/slides/)**

## 1. 강의자료

| 형식 | 파일 | 비고 |
|---|---|---|
| HTML | [slides/index.html](slides/index.html) | 브라우저에서 클릭·←→로 넘김, 복사 버튼 작동 |
| PDF | [slides/강의자료_법률안검토보고서에이전트_20261026.pdf](slides/강의자료_법률안검토보고서에이전트_20261026.pdf) | 정지 화면, 글꼴 내장 |

## 2. 입법조사관용 MCP·API 도구 모음

| 형식 | 파일 |
|---|---|
| HTML | [tools/입법조사관_MCP_API_도구모음.html](tools/입법조사관_MCP_API_도구모음.html) |
| PDF | [tools/입법조사관_MCP_API_도구모음.pdf](tools/입법조사관_MCP_API_도구모음.pdf) |

## 3. 플러그인: 법률안 검토보고서 작성팀(bill-review)

검토설계 → 관문①(설계 판정) → 쟁점 승인 → 자료조사·조문 원장 → 집필 → 조문 대조 검문소 → 관문②(초안 검수) → 한글(.hwpx) 변환

```bash
claude plugin marketplace add parkjui92/AI-Assembly
claude plugin install bill-review@ai-assembly
```

- 설치 뒤 Claude 앱을 다시 시작하고, 같은 작업 폴더에서 "법률안 검토보고서 작성팀의 팀원과 스킬을 표로 보여줘"로 확인
- 법령 현행 확인에는 [korean-law-mcp](https://github.com/chrisryugj/korean-law-mcp), 한글 문서 읽기·변환에는 [kordoc](https://github.com/chrisryugj/kordoc) 연결 권장
- 인증키(국가법령정보 OC 등)는 채팅창이 아니라 작업 폴더의 `.env`에 보관

## 유의

- 초안은 에이전트가, 쟁점 판단과 결론은 작성자가 함
- 비공개 자료·내부 회답·개인정보는 반입 기준을 확인한 뒤 넣음
- 강의자료 출처는 각 슬라이드 아래 줄에 표기

문의: 박주이 · 한양대학교 과학기술정책연구소 · parkjui92@gmail.com
라이선스: 플러그인 MIT(`plugins/bill-review/LICENSE`)
