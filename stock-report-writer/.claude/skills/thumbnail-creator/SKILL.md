# Thumbnail Creator Skill

## 역할
블로그와 유튜브용 썸네일 이미지를 생성합니다.
기존 썸네일 스타일을 분석하여 브랜드 일관성을 유지하면서 클릭률(CTR)을 높이는 디자인을 만듭니다.

## 인풋
- 블로그 제목 (blog-post.md에서)
- 유튜브 제목 (youtube-script.md에서)
- 종목명, 티커, 핵심 키워드

## 아웃풋
- `Outputs/[slug]/thumbnail-blog.png` (1200x628)
- `Outputs/[slug]/thumbnail-youtube.png` (1280x720)

---

## 블로그 썸네일 (1200x628)

### 구성 요소
1. **메인 텍스트**: 종목명 + 핵심 한 줄 (예: "삼성전자 목표주가 분석")
2. **서브 텍스트**: 날짜 or 핵심 수치 (예: "목표주가 OOO원")
3. **비주얼 요소**: 상승 화살표, 주식 차트 라인, 종목 로고 (공개된 경우)
4. **브랜드 요소**: 채널/블로그 로고 or 워터마크

### 프롬프트 템플릿
```
Create a blog thumbnail image (1200x628 pixels) for a stock analysis post.
Title: [블로그 제목]
Stock: [종목명]
Key number: [목표주가 or 핵심 수치]

Design requirements:
- Clean, professional financial blog style
- High contrast text for readability
- Include subtle stock chart or arrow visual
- Brand color scheme: [references/thumbnail-examples/ 참조]
- Korean text must be clear and readable
- Bottom area: blog/channel name watermark
```

---

## 유튜브 썸네일 (1280x720)

### 클릭률 높이는 원칙
1. **큰 텍스트**: 5단어 이내, 원거리에서도 읽힐 크기
2. **강한 대비**: 밝은 배경 + 어두운 텍스트 or 반대
3. **감정 유발**: 숫자, 의문형, 충격적 사실 활용
4. **시선 집중점**: 중앙 or 좌측 상단에 핵심 메시지

### 구성 요소
1. **메인 텍스트**: 핵심 키워드 (예: "지금 사야해?", "목표주가 OOO원")
2. **종목명 배지**: 종목명 + 티커 강조 박스
3. **방향 아이콘**: 상승↑ / 하락↓ 화살표 (분석 방향에 따라)
4. **배경**: 금융 테마 (차트, 그래프, 빌딩 등)

### 프롬프트 템플릿
```
Create a YouTube thumbnail (1280x720 pixels) for a stock analysis video.
Main text: [유튜브 제목의 핵심 5단어]
Stock name: [종목명]
Direction: [상승 전망 / 하락 전망 / 중립]

Design requirements:
- Eye-catching, high CTR design
- Bold, large Korean text
- Strong color contrast (use red/green for financial context)
- Include stock ticker badge: [티커]
- Thumbnail style: reference thumbnails/thumbnail-examples/ folder
- Professional but attention-grabbing
```

---

## 기존 스타일 참조 방법

`references/thumbnail-examples/` 폴더의 기존 썸네일을 분석하여:
1. 주로 사용하는 색상 팔레트 파악
2. 텍스트 레이아웃 패턴 파악
3. 브랜드 요소 위치 파악
→ 동일한 스타일로 재현

---

## 주의사항
- 타 회사의 공식 로고는 무단 사용 금지 (종목명 텍스트로 대체)
- 과도한 클릭베이트 금지 ("무조건 오른다" 등 단정적 표현)
- 생성된 썸네일은 반드시 품질 확인 후 저장
- 생성 실패 시 오케스트레이터에 보고 (나머지 작업은 계속)

## 참조 파일
- `references/thumbnail-examples/` - 기존 썸네일 이미지들 (스타일 재현용)
  → 실제 썸네일 이미지를 이 폴더에 추가해야 품질이 높아짐!
