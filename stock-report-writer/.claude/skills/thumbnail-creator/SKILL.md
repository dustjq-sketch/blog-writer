# Thumbnail Creator Skill

## 역할
쇼츠용 세로형 썸네일과 풀영상용 가로형 썸네일을 생성합니다.
Gemini 2.0 Flash를 사용합니다.

## 인풋
- `Outputs/[slug]/summary.md` (종목명, 목표주가, 핵심 메시지)
- `Outputs/[slug]/shorts-script.md` (쇼츠 제목)
- `Outputs/[slug]/youtube-script.md` (풀영상 제목)

## 아웃풋
- `Outputs/[slug]/thumbnail-shorts.png` (1080x1920 세로형)
- `Outputs/[slug]/thumbnail-youtube.png` (1280x720 가로형)

---

## 쇼츠 썸네일 (1080x1920 세로형)

### 구성
- **상단**: 종목명 + 목표주가 (크고 굵게)
- **중단**: 상승여력 % (임팩트 있게)
- **하단**: 증권사명 + 날짜

### 클릭 유발 포인트
- 목표주가 숫자를 가장 크게
- 상승여력 색상: 빨간색 (한국 주식 관행: 빨강 = 상승)
- 배경: 어두운 계열 (숫자가 더 잘 보임)

프롬프트:
```
Create a YouTube Shorts thumbnail (1080x1920px, vertical).
Stock: [종목명]
Target price: OOO원
Upside: +OO%
Securities: [증권사명]

Design requirements:
- Very large, bold Korean text for the price
- Upside percentage in bright red (Korean convention)
- Dark background (navy or black) for contrast
- Clean, professional financial style
- Eye-catching even on small mobile screen
- Bottom: channel/brand name small text
Style reference: thumbnail-examples/ folder
```

---

## 풀영상 썸네일 (1280x720 가로형)

### 구성
- **좌측**: 종목명 + 핵심 문구 (5단어 이내)
- **우측**: 목표주가 큰 숫자 or 차트 이미지
- **하단**: 증권사명 + 날짜

### 클릭 유발 포인트
- 강한 대비 색상
- 의문형 or 숫자형 제목 ("OOO원이 맞을까?", "목표주가 OOO원!")

프롬프트:
```
Create a YouTube thumbnail (1280x720px, horizontal/landscape).
Video title: [유튜브 영상 제목]
Stock: [종목명]
Target price: OOO원
Upside: +OO%

Design requirements:
- Bold, large Korean text (readable from distance)
- Strong color contrast
- Professional financial design
- Include stock name badge
- Right side: price numbers or upward arrow
Style reference: thumbnail-examples/ folder
```

---

## 기존 썸네일 스타일 참조

`references/thumbnail-examples/` 폴더에 기존 썸네일 이미지를 넣어두면 더 정확한 스타일 재현이 가능합니다.
- 최소 3~5개 이상 권장
- 쇼츠용 세로형 + 유튜브용 가로형 구분해서 넣기

---

## 주의사항
- 타 회사 공식 로고 무단 사용 금지 (종목명 텍스트로 대체)
- "무조건 오른다" 등 단정적 표현 금지
- 생성 실패 시 Report Producer에 보고 (나머지 진행)

## 참조 파일
- `references/thumbnail-examples/` - 기존 썸네일 이미지 (스타일 재현용)
