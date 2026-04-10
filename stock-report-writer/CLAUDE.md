# 리포트읽어드림 — 증권사 리포트 → 유튜브 자동화 시스템

유튜브 채널 "리포트읽어드림"을 위한 콘텐츠 자동화 파이프라인.
증권사 리포트(PDF/이미지)를 입력받아 유튜브 쇼츠/풀영상을 자동 생성합니다.

---

## 현재 구현 상태 (2026-04-10 기준)

### Flask 대시보드 (포트 5001)
- `server/app.py` — Flask 백엔드
- `server/templates/index.html` — 대시보드 UI
- 서버 시작: `서버시작.command` 더블클릭 또는 `python3 server/app.py`

### 세 가지 파이프라인

| 탭 | 입력 | 출력 | 영상 형식 |
|---|---|---|---|
| 증권사 리포트 | 리포트 이미지 | 쇼츠 (세로 9:16) | 30~60초 |
| 산업 리포트 | PDF | 풀영상 (가로 16:9) | 5~8분 |
| 경제 용어 | 텍스트 입력 | 쇼츠 (세로 9:16) | 30~60초 |

### 반자동 이미지 파이프라인 (핵심)
1. 대시보드에서 리포트/용어 입력
2. AI가 대본 생성 + 이미지 프롬프트 생성 (`status="prompts_ready"`)
3. 사용자가 프롬프트를 Gemini에서 이미지 생성
4. 생성한 이미지를 대시보드에 업로드
5. 시스템이 자동으로 영상 제작

---

## 핵심 파일

### `scripts/produce.py`
영상 제작 스크립트 (Google Cloud TTS + MoviePy)

- `generate_audio(slug, video_type, is_term)` — TTS 음성 생성
  - `speaking_rate=0.95` (용어), `1.1` (나머지)
  - 모델: `ko-KR-Neural2-C`
- `generate_video(slug, video_type, is_term)` — 영상 합성
  - `FADE=1.2` (용어), `0.6` (나머지)
  - `DISC_DUR=6` (면책 카드 6초)
  - `total_img_time = max(audio.duration - DISC_DUR + n * FADE + 0.5, n * 2.0)`
- `generate_term_images()` — 경제용어 카드 이미지 생성 (PIL)
- `_clean(text)` — PIL 렌더링 불가 문자 제거 (이모지 등)
- 실행 모드: `term-video`, `shorts-video`, `industry-video`

### `server/app.py`
Flask 백엔드

- `create_stock_image_prompts(d)` — 주식 카드 3장 프롬프트 (목표주가+상승여력 강조)
- `create_industry_image_prompts(d)` — 산업 슬라이드 8장 프롬프트
- `create_term_image_prompts(d)` — 경제용어 카드 4장 프롬프트
- `process_job()` — 대본+프롬프트 생성 후 `status="prompts_ready"` 반환
- `process_term_job()` — 경제용어 버전
- `/upload-images` — 이미지 업로드 → `process_video_job()` 시작
- `process_video_job()` — `produce.py slug [term|shorts|industry]-video` 실행

### `server/templates/index.html`
대시보드 UI

- 3개 탭: 증권사 리포트 / 산업 리포트 / 경제 용어
- 프롬프트 패널: 2열 그리드, 복사 버튼
- `accumulatedFiles[]` — 파일 누적 업로드 (여러 번 선택 가능)
- `pollStatus()` — `prompts_ready` 상태 감지 → 프롬프트 패널 표시
- `reset()` — null-safe, `setMode(currentMode)` 호출

---

## 폴더 구조

```
stock-report-writer/
├── CLAUDE.md                    # 이 파일
├── server/
│   ├── app.py                   # Flask 백엔드
│   └── templates/
│       └── index.html           # 대시보드 UI
├── scripts/
│   └── produce.py               # TTS + 영상 제작
├── reports/                     # 증권사 리포트 PDF
├── uploads/                     # 업로드된 이미지 (gitignore)
├── Outputs/                     # 생성된 영상/음성 (gitignore)
│   └── [slug]/
│       ├── images/              # 업로드된 이미지
│       ├── audio-*.mp3
│       ├── *-video.mp4
│       └── *-script.md
├── requirements.txt
├── .env                         # API 키 (gitignore)
└── 서버시작.command              # 더블클릭으로 서버 시작
```

---

## 환경 설정

```bash
# .env 파일 필요
GOOGLE_APPLICATION_CREDENTIALS=./subiblog-writer-XXXXXX.json
GEMINI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
```

```bash
# 패키지 설치
pip install -r requirements.txt
```

---

## Git 설정

- GitHub repo: `dustjq-lab/stock-report-writer`
- remote: `git@github.com:dustjq-lab/stock-report-writer.git`
- 서버용 remote: `dustjq` (Mac 서버에서 pull 받을 때)

---

## 주요 해결된 버그 이력

- PIL 이모지/특수문자 → `_clean()` 으로 제거
- 카드 텍스트 overflow → box height 증가, 3줄 제한
- 면책 음성 잘림 → `DISC_DUR=6`, `+0.5s` 버퍼
- 면책 중복 → 스크립트 템플릿에서 제거 (`extract_narration`이 추가)
- reset() 크래시 → null 체크, span 제거
- 경제용어 탭 버튼 불작동 → duplicate `const countEl` 제거
- 복사 버튼 불작동 → `execCommand` fallback 사용

---

## 핵심 주의사항

1. **리포트 내용만 사용** — 추측/외부 정보 추가 금지
2. **면책 문구 필수** — `extract_narration()`이 자동 추가, 스크립트 템플릿에 넣으면 중복
3. **이미지 업로드 순서** — 프롬프트 번호 순서대로 업로드
4. `produce.py` 직접 실행 시 slug 폴더에 `images/` 있어야 함
