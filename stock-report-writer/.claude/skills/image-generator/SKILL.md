# Image Generator Skill

## 역할
summary.md의 수치 데이터를 바탕으로 영상에 활용할 차트와 인포그래픽을 생성합니다.
Gemini 2.0 Flash를 사용합니다.

## 인풋
- `Outputs/[slug]/summary.md`

## 아웃풋
- `Outputs/[slug]/images/` 폴더 내 이미지들

---

## 생성할 이미지 목록

### 이미지 1: 목표주가 비교 카드 (필수)
**파일명**: `[slug]-price-card.png`
**사이즈**: 1080x1080 (정사각형, 쇼츠/유튜브 썸네일 공용)
**내용**:
- 현재가 vs 목표주가 시각적 비교
- 상승여력 % 크게 표시
- 증권사명 + 날짜

프롬프트:
```
Create a stock price comparison card (1080x1080px).
Stock: [종목명]
Current price: OOO원
Target price: OOO원
Upside: +OO%
Securities firm: [증권사명]

Design: Clean financial card, large numbers, 
upside arrow ↑ in green/red (Korean convention: red = up),
professional but visually striking.
Korean text, white background.
```

### 이미지 2: 핵심 이유 인포그래픽 (필수)
**파일명**: `[slug]-reasons.png`
**사이즈**: 1080x1350 (세로형, 쇼츠 본문용)
**내용**:
- 핵심 이유 2~3가지를 카드형으로 나열
- 각 이유당 아이콘 + 제목 + 핵심 수치

프롬프트:
```
Create a vertical infographic (1080x1350px) showing key investment reasons.
Stock: [종목명]

Reason 1: [이유 제목] - [핵심 수치]
Reason 2: [이유 제목] - [핵심 수치]
Reason 3: [이유 제목] - [핵심 수치] (if exists)

Design: Card-style layout, numbered list,
icons for each reason, professional financial look.
Korean text, clean background.
```

### 이미지 3: 실적/지표 차트 (선택)
**파일명**: `[slug]-chart.png`
**사이즈**: 1280x720
**생성 조건**: summary.md에 분기별 실적 데이터가 있을 때만

---

## 생성 후 처리
1. `Outputs/[slug]/images/` 에 저장
2. `shorts-script.md`의 화면 구성 표에 이미지 파일명 업데이트
3. `youtube-script.md`의 `[차트 등장]` 큐에 이미지 파일명 업데이트

---

## 스타일 가이드
`references/image-style-guide.md` 참조

## 주의사항
- 리포트에 없는 수치 삽입 금지
- 생성 실패 시 스킵 후 Report Producer에 보고

## 참조 파일
- `references/image-style-guide.md` - 색상, 레이아웃 스타일
