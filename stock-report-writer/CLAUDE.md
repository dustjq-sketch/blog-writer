# 증권사 리포트 → 유튜브 콘텐츠 자동화 시스템

증권사 리포트(PDF 또는 MD 파일)를 입력받아 다음을 자동 생성합니다:
- **유튜브 쇼츠 스크립트** (30~60초) ← 핵심 산출물
- **유튜브 풀영상 스크립트** (5~8분)
- **차트 & 인포그래픽 이미지** (본문용)
- **썸네일** (쇼츠용 + 풀영상용)

블로그 글은 별도 시스템에서 운영 중이므로 이 프로젝트에서는 제외합니다.

---

## 사용 방법

```bash
# 방법 1: 파일을 reports/ 폴더에 넣고 요청
"reports/삼성전자-한국투자증권-20260405.pdf 로 콘텐츠 만들어줘"

# 방법 2: 파일 직접 첨부 후 요청
"이 리포트로 쇼츠 스크립트랑 썸네일 만들어줘"

# 방법 3: 여러 리포트 한번에
"reports/ 폴더에 있는 리포트 3개 전부 콘텐츠 만들어줘"
```

---

## 워크플로우

```
리포트 파일 (PDF or MD)
        ↓
[Report Producer Agent]
        │
        Step 1: Report Parser Skill
        │       리포트에서 핵심 정보 추출
        │       → 종목명, 목표주가, 핵심 이유 3가지, 리스크
        │       → Outputs/[slug]/summary.md 저장
        │
        Step 2~4: 병렬 실행 ──────────────────────────┐
        │                                             │
        ▼                                             ▼
[Shorts Writer Skill]                    [YouTube Script Skill]
  30~60초 쇼츠 스크립트                    5~8분 풀영상 스크립트
  → shorts-script.md                    → youtube-script.md
        │
        Step 3: Image Generator Skill (병렬)
        │       목표주가 비교 카드, 핵심 지표 인포그래픽
        │       → images/ 폴더
        │
        Step 5: Thumbnail Creator Skill
                쇼츠 썸네일 (1080x1920 세로)
                풀영상 썸네일 (1280x720 가로)
                → thumbnail-shorts.png
                → thumbnail-youtube.png
```

---

## 폴더 구조

```
stock-report-writer/
├── CLAUDE.md                           # 이 파일 (전체 시스템 설명)
│
├── reports/                            # 리포트 파일 넣는 곳 (PDF or MD)
│   └── (여기에 증권사 리포트 파일 추가)
│
├── .claude/
│   ├── agents/
│   │   └── report-producer.md          # 전체 프로세스 총괄
│   └── skills/
│       ├── report-parser/
│       │   ├── SKILL.md                # 리포트 핵심 정보 추출
│       │   └── references/
│       │       └── report-examples.md  # 파싱 예시
│       ├── shorts-writer/
│       │   ├── SKILL.md                # 30~60초 쇼츠 스크립트 작성
│       │   └── references/
│       │       └── shorts-examples.md  # 쇼츠 스크립트 예시
│       ├── youtube-script/
│       │   ├── SKILL.md                # 5~8분 풀영상 스크립트 작성
│       │   └── references/
│       │       └── script-examples.md  # 풀영상 스크립트 예시
│       ├── image-generator/
│       │   ├── SKILL.md                # 차트 & 인포그래픽 생성 (Gemini)
│       │   └── references/
│       │       └── image-style-guide.md
│       └── thumbnail-creator/
│           ├── SKILL.md                # 썸네일 생성 (Gemini)
│           └── references/
│               └── thumbnail-examples/ # 기존 썸네일 (스타일 참조용)
│
└── Outputs/
    ├── history.md                      # 작업 히스토리 (누적)
    └── [ticker-YYYYMMDD]/              # 예: samsung-20260405
        ├── summary.md                  # 파싱된 핵심 요약
        ├── shorts-script.md            # 쇼츠 스크립트 (30~60초)
        ├── youtube-script.md           # 풀영상 스크립트 (5~8분)
        ├── images/                     # 차트, 인포그래픽
        ├── thumbnail-shorts.png        # 쇼츠 썸네일 (세로형)
        └── thumbnail-youtube.png       # 풀영상 썸네일 (가로형)
```

---

## 에이전트 vs 스킬 역할

| 역할 | 파일 | 유형 |
|------|------|------|
| 전체 총괄 | `agents/report-producer.md` | Agent |
| 리포트 파싱 | `skills/report-parser/` | Skill |
| 쇼츠 스크립트 | `skills/shorts-writer/` | Skill |
| 풀영상 스크립트 | `skills/youtube-script/` | Skill |
| 차트/인포그래픽 | `skills/image-generator/` | Skill |
| 썸네일 | `skills/thumbnail-creator/` | Skill |

---

## 핵심 주의사항

1. **리포트 내용만 사용**: 추측이나 외부 정보 추가 금지
2. **쇼츠 시간 엄수**: 한국어 75~150단어 (30~60초)
3. **면책 문구 필수**: 모든 스크립트 마지막에 포함
4. **전문 용어 변환**: PER, YoY 등은 쉬운 말로 풀어서
