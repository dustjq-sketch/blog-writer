# Image Generator Skill

## 역할
brief.md의 수치 데이터를 바탕으로 블로그 본문에 삽입할 이미지를 생성합니다.
Gemini 2.0 Flash를 사용하여 차트, 인포그래픽, 비교 다이어그램을 생성합니다.

## 인풋
- `Outputs/[slug]/brief.md` (수치 데이터 참조)

## 아웃풋
- `Outputs/[slug]/images/` 폴더 내 이미지 파일들

---

## 생성할 이미지 목록

### 이미지 1: 실적 비교 차트 (필수)
**파일명**: `[slug]-chart-01.png`
**사이즈**: 800x500
**내용**: 최근 4분기 매출 + 영업이익 바 차트
**스타일**: `references/image-style-guide.md` 참조

프롬프트 템플릿:
```
Create a clean bar chart showing [종목명]'s quarterly performance.
Data: [brief.md의 실적 데이터 삽입]
Style: Modern, professional financial chart. 
Colors: Use brand-consistent colors from style guide.
Include: Quarter labels (Q1-Q4), value labels on bars, YoY growth rate.
Language: Korean labels.
Background: White or light gray.
```

### 이미지 2: 핵심 지표 인포그래픽 (필수)
**파일명**: `[slug]-infographic-01.png`
**사이즈**: 800x500
**내용**: 목표주가, PER, PBR, 영업이익률 등 핵심 수치 카드형

프롬프트 템플릿:
```
Create a financial metrics infographic card for [종목명].
Metrics to show:
- Current price: OOO원
- Target price: OOO원 (↑OO%)
- PER: OO배
- PBR: O.O배
- Operating margin: OO%
Style: Clean card design, easy to read at a glance.
Colors: Green for positive, Red for negative/risk.
Language: Korean.
```

### 이미지 3: 비교 다이어그램 (선택)
**파일명**: `[slug]-compare-01.png`
**사이즈**: 800x500
**내용**: 경쟁사 대비 포지셔닝 or 섹터 내 위치

생성 조건: brief.md에 경쟁사 비교 데이터가 있을 때만 생성

---

## 이미지 생성 방법 (Gemini 2.0 Flash)

```python
import google.generativeai as genai

model = genai.GenerativeModel('gemini-2.0-flash-exp')
response = model.generate_content([프롬프트])
# 이미지 저장
```

또는 Claude Code의 이미지 생성 도구 활용.

---

## 생성 후 처리

1. 이미지 생성 완료 후 `Outputs/[slug]/images/` 폴더에 저장
2. `blog-post.md`의 플레이스홀더 교체:
   - `{{IMAGE_CHART_01}}` → `![실적 비교 차트](images/[slug]-chart-01.png)`
   - `{{IMAGE_INFOGRAPHIC_01}}` → `![핵심 지표](images/[slug]-infographic-01.png)`

---

## 주의사항
- 이미지에 허위 데이터 삽입 금지 (brief.md의 수치만 사용)
- 생성 실패 시 스킵 후 오케스트레이터에 보고 (콘텐츠 제작은 계속 진행)
- 이미지에도 면책 문구 작은 글씨로 포함: "출처: [리포트 출처]"

## 참조 파일
- `references/image-style-guide.md` - 색상, 폰트, 레이아웃 스타일 가이드
