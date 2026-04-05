# 주식 리포트 콘텐츠 자동화 시스템

주식 리포트를 수집·분석하여 블로그 글과 유튜브 스크립트를 자동으로 생성하는 멀티 에이전트 시스템입니다.
zoey.day의 블로그 자동화 구조를 참고하여, 각 종목마다 독립적인 오케스트레이터를 할당하는 패턴으로 설계되었습니다.

---

## 시스템 철학

- **에이전트 vs 스킬 구분**: 판단이 필요한 역할은 에이전트, 가이드라인만 필요한 역할은 스킬
- **오케스트레이터 패턴**: 각 종목마다 독립적인 Report Orchestrator 할당 → 컨텍스트 명확, 에러 격리, 병렬 처리
- **레퍼런스 우선**: 각 스킬의 references/ 폴더에 충분한 예시를 넣어야 결과물 품질이 높아짐
- **MECE 관리**: stock-watchlist.md로 중복 종목 방지, 누적 히스토리 관리

---

## 워크플로우

```
User Input ("오늘 분석할 종목 추천해줘" or 직접 종목 입력)
    ↓
[Stock Hunter Agent] - 종목 3~5개 발굴 + 리포트 출처 제안
    ↓
사용자 선택 (종목 2~3개 선택)
    ↓
    ┌──────────────────┼──────────────────┐
    ▼                  ▼                  ▼
Report Orch. #1   Report Orch. #2   Report Orch. #3   ← 병렬 실행!
    │
    Phase 1: 리포트 수집 & 핵심 분석 (Stock Analyst Skill)
    Phase 2: 블로그 글 작성 (Blog Writer Skill)
    Phase 3: 유튜브 스크립트 작성 (YouTube Script Skill)
    Phase 4: 본문 이미지 생성 (Image Generator Skill)
    Phase 5: 썸네일 생성 (Thumbnail Creator Skill)
    Phase 6: 메타데이터 생성 (slug, 태그, 디스크립션)
    │
    └──────────────────┼──────────────────┘
                       ▼
    [Content Reviewer Agent] - 팩트 체크 + 통합 검수 + 발행 전략
                       ↓
    Outputs/[slug]/ 폴더에 정리 저장
```

---

## 프로젝트 구조

```
stock-report-writer/
├── CLAUDE.md                          # 이 파일 (전체 시스템 설명서)
├── ORCHESTRATOR.md                    # 오케스트레이터 상세 기획서
│
├── .claude/
│   ├── agents/
│   │   ├── stock-hunter.md            # 종목 발굴 에이전트
│   │   ├── report-orchestrator.md     # 종목별 전체 프로세스 오케스트레이터 (병렬)
│   │   └── content-reviewer.md        # 콘텐츠 검수 에이전트 (일괄)
│   │
│   └── skills/
│       ├── stock-analyst/
│       │   ├── SKILL.md               # 리포트 분석 & 핵심 요약 스킬
│       │   └── references/
│       │       ├── report-examples.md # 잘 정리된 리포트 요약 예시
│       │       └── stock-terminology.md # 주식 용어 사전 (독자 친화적 설명)
│       │
│       ├── blog-writer/
│       │   ├── SKILL.md               # SEO 블로그 글 작성 스킬
│       │   └── references/
│       │       ├── blog-examples.md   # 기존 블로그 글 예시 (톤앤매너)
│       │       └── cta-templates.md   # CTA 문구 모음
│       │
│       ├── youtube-script/
│       │   ├── SKILL.md               # 유튜브 스크립트 작성 스킬
│       │   └── references/
│       │       └── script-examples.md # 유튜브 스크립트 예시 (후크, 구성)
│       │
│       ├── image-generator/
│       │   ├── SKILL.md               # 본문 이미지 생성 스킬 (gemini-2.0-flash)
│       │   └── references/
│       │       └── image-style-guide.md # 이미지 스타일 가이드
│       │
│       └── thumbnail-creator/
│           ├── SKILL.md               # 썸네일 생성 스킬 (gemini-2.0-flash)
│           └── references/
│               └── thumbnail-examples/ # 기존 썸네일 이미지들 (스타일 참조)
│
└── Outputs/
    ├── stock-watchlist.md             # 분석한 종목 히스토리 (누적, 중복 방지)
    ├── report-briefs.md               # 리포트 기획서 히스토리 (누적)
    ├── content-review.md              # 콘텐츠 검수 보고서
    └── [slug]/                        # 종목별 결과물 폴더 (예: samsung-q1-2026)
        ├── brief.md                   # 분석 기획서
        ├── blog-post.md               # 블로그 글 (마크다운)
        ├── youtube-script.md          # 유튜브 스크립트
        ├── images/                    # 본문 이미지
        ├── thumbnail.png              # 썸네일
        └── metadata.json             # SEO 메타데이터 (제목, 디스크립션, 태그, slug)
```

---

## 에이전트 역할 요약

| 역할 | 파일 | 유형 | 설명 |
|------|------|------|------|
| Stock Hunter | `agents/stock-hunter.md` | Agent | 시장 트렌드 분석, 오늘 주목할 종목 3~5개 발굴 |
| Report Orchestrator | `agents/report-orchestrator.md` | Agent | 1개 종목의 전체 콘텐츠 제작 총괄 (병렬 실행) |
| Content Reviewer | `agents/content-reviewer.md` | Agent | 팩트 체크, SEO 검수, 발행 순서 전략 |
| Stock Analyst | `skills/stock-analyst/` | Skill | 리포트 수집·분석·핵심 3가지 요약 |
| Blog Writer | `skills/blog-writer/` | Skill | SEO 최적화 블로그 글 작성 |
| YouTube Script | `skills/youtube-script/` | Skill | 유튜브 스크립트 (후크 → 본론 → CTA) |
| Image Generator | `skills/image-generator/` | Skill | 차트, 인포그래픽, 비교 이미지 생성 |
| Thumbnail Creator | `skills/thumbnail-creator/` | Skill | 블로그·유튜브 썸네일 생성 |

---

## 실행 방법

```bash
# 1. 종목 발굴
"오늘 주목할 주식 종목 추천해줘"

# 2. 특정 종목 직접 지정
"삼성전자, SK하이닉스, NVIDIA 리포트 콘텐츠 만들어줘"

# 3. 섹터 기반 발굴
"반도체 섹터에서 이번 주 실적 발표 종목 분석해줘"
```

---

## 핵심 주의사항

1. **레퍼런스 폴더 채우기**: 각 스킬의 references/ 폴더에 예시 자료를 충분히 넣어야 품질이 높아짐
2. **팩트 체크 필수**: 주식 정보는 오류가 있으면 안 되므로 Content Reviewer의 팩트 체크를 반드시 거침
3. **면책 문구**: 모든 콘텐츠에 "본 콘텐츠는 투자 권유가 아닌 정보 제공 목적입니다" 문구 포함
4. **stock-watchlist.md 누적 관리**: 이미 만든 종목+날짜는 기록하여 중복 콘텐츠 방지
