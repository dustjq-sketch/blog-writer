# 썸네일 스타일 가이드 (리포트읽어드림)

실제 생성된 썸네일 기준으로 스타일을 정리합니다.
새 종목 썸네일 생성 시 이 스타일을 그대로 재현하세요.

---

## 확정된 썸네일 스타일

### 쇼츠 썸네일 (1080x1920 세로형)

**배경**: 다크 네이비 (#0D1B2A 계열)
**레이아웃 (위→아래)**:
1. 종목명 — 흰색, 매우 크고 굵게, 상단 중앙
2. 목표주가 (원) — 빨간색, 크게
3. 상승여력 (%) — 빨간색 + 빨간색 화살표 ↑, 가장 크게
4. 하단 — "증권사명 리포트 | 날짜" 작은 회색 텍스트 + 브랜드 아이콘(✦)

**예시 (삼성전기)**:
```
삼성전기           ← 흰색 대형
590,000원          ← 빨간색
+41.5%↑           ← 빨간색 최대 크기
유진투자증권 리포트 | 2026.04.03  ✦
```

### 가로형 카드 (목표주가 비교 카드, 1080x540 내외)

**배경**: 다크 네이비
**레이아웃**:
- 좌상단: 증권사명 | 날짜 (작은 회색)
- 종목명 + 티커 (흰색, 중간 크기)
- 현재가 (흰색)
- 목표주가 (빨간색, 크게) + (상향 전 가격 소자)
- 상승여력 ▲ % (빨간색, 가장 크게)

---

## 생성 프롬프트 템플릿 (확정)

### 쇼츠 썸네일
```
Create a YouTube Shorts thumbnail (1080x1920px, vertical).

Style reference: dark navy background (#0D1B2A), Korean financial channel style.

Layout (top to bottom):
1. Stock name "[종목명]" — white, very large bold font, top center
2. Target price "[목표주가]원" — bright red, large
3. Upside "[상승여력]%↑" — bright red with red arrow, largest element
4. Bottom small text: "[증권사명] 리포트 | [날짜]" in gray + small ✦ diamond icon

Design rules:
- Minimal, high contrast, mobile-first
- Korean text
- No clutter, just the numbers
- Arrow graphic (subtle, dark gray) in background pointing up-right
```

### 목표주가 비교 카드
```
Create a stock price card image (1080x540px).

Style: dark navy background, Korean financial design.

Content:
- Top left small text: "[증권사명] | [날짜]" (gray)
- "[종목명] ([티커])" — white, medium
- "현재가  [현재가]원" — white, large
- "목표주가  [목표주가]원  (상향 전 [이전목표주가]원)" — bright red, large
- "상승여력 ▲ +[상승여력]%" — bright red, very large, bold

Same style as the Shorts thumbnail.
```

---

*2026-04-03 삼성전기 리포트 기준으로 확정된 스타일입니다.*
