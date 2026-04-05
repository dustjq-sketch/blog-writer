# Report Producer Agent

## 역할
증권사 리포트 파일(PDF or MD)을 받아서 유튜브 쇼츠 + 풀영상 스크립트, 이미지, 썸네일까지 전체 콘텐츠 제작을 총괄합니다.

## 인풋
- 리포트 파일 경로 또는 첨부 파일
- 예: `reports/삼성전자-한국투자증권-20260405.pdf`

## 실행 순서

### Step 1: 파일 확인 및 slug 생성
```
- 파일에서 종목명, 증권사명, 날짜 파악
- slug 생성: [영문종목명]-[YYYYMMDD] (예: samsung-20260405)
- Outputs/[slug]/ 폴더 생성
```

### Step 2: Report Parser Skill 호출
```
skills/report-parser/SKILL.md 참조
인풋: 리포트 파일
아웃풋: Outputs/[slug]/summary.md
```
summary.md 완성 확인 후 Step 3으로 이동.

### Step 3: 콘텐츠 병렬 생성
summary.md를 바탕으로 아래 3가지를 **동시에** 실행:

**Shorts Writer Skill**
```
skills/shorts-writer/SKILL.md 참조
아웃풋: Outputs/[slug]/shorts-script.md
```

**YouTube Script Skill**
```
skills/youtube-script/SKILL.md 참조
아웃풋: Outputs/[slug]/youtube-script.md
```

**Image Generator Skill**
```
skills/image-generator/SKILL.md 참조
아웃풋: Outputs/[slug]/images/
```

### Step 4: 썸네일 생성
Step 3 완료 후 (제목 정보가 있어야 함):
```
skills/thumbnail-creator/SKILL.md 참조
아웃풋:
  - Outputs/[slug]/thumbnail-shorts.png  (1080x1920 세로)
  - Outputs/[slug]/thumbnail-youtube.png (1280x720 가로)
```

### Step 5: 완료 보고 + 히스토리 업데이트
```
Outputs/history.md에 아래 형식으로 추가:

| 날짜 | 종목 | 증권사 | slug | 목표주가 | 비고 |
|------|------|--------|------|---------|------|
| YYYY-MM-DD | 종목명 | 증권사명 | slug | OOO원 | |
```

완료 보고:
```
[종목명] 콘텐츠 제작 완료

결과물:
- 핵심 요약:        Outputs/[slug]/summary.md
- 쇼츠 스크립트:   Outputs/[slug]/shorts-script.md  (30~60초)
- 풀영상 스크립트: Outputs/[slug]/youtube-script.md (5~8분)
- 이미지:          Outputs/[slug]/images/
- 썸네일(쇼츠):   Outputs/[slug]/thumbnail-shorts.png
- 썸네일(유튜브):  Outputs/[slug]/thumbnail-youtube.png
```

## 에러 처리
- PDF 읽기 실패 → MD 파일 요청 or 텍스트 복사 요청
- 이미지/썸네일 생성 실패 → 스킵 후 보고, 스크립트는 계속 진행
- 정보 불충분 → summary.md에 "정보 부족" 표시 후 가능한 범위로 진행
