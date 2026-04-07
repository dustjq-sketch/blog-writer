"""
리포트읽어드림 - 자동화 대시보드 서버
Usage: python3 server/app.py
"""

import os, subprocess, threading, uuid, json, re, io, traceback
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

gac = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
if gac and not os.path.isabs(gac):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(BASE_DIR / gac.lstrip("./"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OUTPUTS_DIR = BASE_DIR / "Outputs"
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
jobs = {}  # job_id → {status, step, message, slug}


# ─────────────────────────────────────────
# Gemini로 리포트 이미지 파싱
# ─────────────────────────────────────────

def extract_report_data(image_path: Path) -> dict:
    from google import genai
    from google.genai import types
    from PIL import Image

    client = genai.Client(api_key=GEMINI_API_KEY)

    img = Image.open(str(image_path)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    prompt = """이 증권사 리포트 이미지에서 다음 정보를 JSON으로 추출해줘.
다른 텍스트 없이 JSON만 출력해줘.

{
  "stock_name": "종목명(한글)",
  "stock_code": "종목코드(숫자만)",
  "broker": "증권사명",
  "date": "발행일(YYYY-MM-DD)",
  "opinion": "BUY/HOLD/SELL",
  "target_price": "목표주가(예:590,000원)",
  "current_price": "현재가(예:417,000원)",
  "upside": "상승여력(예:+41.5%)",
  "reason1_title": "핵심이유1 제목(15자 이내)",
  "reason1_body": "핵심이유1 설명(2문장)",
  "reason2_title": "핵심이유2 제목(15자 이내)",
  "reason2_body": "핵심이유2 설명(2문장)",
  "reason3_title": "핵심이유3 제목(15자 이내)",
  "reason3_body": "핵심이유3 설명(2문장)",
  "metrics": [
    {"item": "항목명", "value": "수치", "change": "증감"}
  ],
  "risk": "주요리스크(1문장)"
}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            prompt,
        ],
    )

    text = response.text.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(m.group() if m else text)


def make_slug(data: dict) -> str:
    name_map = {
        "삼성전기": "semco", "대덕전자": "daedeok", "네오티스": "neotis",
        "심텍": "simtec", "HD현대중공업": "hdhhi", "현대중공업": "hdhhi",
        "SK하이닉스": "skhynix", "삼성전자": "sec", "LG에너지솔루션": "lges",
    }
    name = data.get("stock_name") or ""
    code = data.get("stock_code") or "0"
    raw_date = data.get("date") or ""
    # N/A, 없음, 미상 등 무효값 처리
    if raw_date.strip() in ("N/A", "n/a", "없음", "미상", "unknown", "-"):
        raw_date = ""
    date = re.sub(r"[^\d]", "", raw_date)  # 숫자만 남기기 (슬래시 등 제거)
    en = name_map.get(name, f"s{code}")
    return f"{en}-{date}" if date else en


# ─────────────────────────────────────────
# 콘텐츠 파일 생성
# ─────────────────────────────────────────

def create_content_files(slug: str, d: dict):
    out = OUTPUTS_DIR / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / "images").mkdir(exist_ok=True)

    name    = d.get("stock_name") or ""
    code    = d.get("stock_code") or ""
    broker  = d.get("broker") or ""
    date    = d.get("date") or ""
    opinion = d.get("opinion") or "BUY"
    target  = d.get("target_price") or ""
    current = d.get("current_price") or ""
    upside  = d.get("upside") or ""
    r1t = d.get("reason1_title", ""); r1b = d.get("reason1_body", "")
    r2t = d.get("reason2_title", ""); r2b = d.get("reason2_body", "")
    r3t = d.get("reason3_title", ""); r3b = d.get("reason3_body", "")
    risk    = d.get("risk", "")
    metrics = d.get("metrics", [])

    m_rows = "| 항목 | 수치 | 증감 |\n|------|------|------|\n"
    for m in metrics[:6]:
        m_rows += f"| {m.get('item','')} | {m.get('value','')} | {m.get('change','')} |\n"

    # summary.md
    (out / "summary.md").write_text(f"""# {name} ({code}) 리포트 핵심 요약
- **증권사**: {broker}
- **발행일**: {date}
- **투자의견**: {opinion} (유지)

---

## 목표주가
- 현재가: **{current}**
- 목표주가: **{target}**
- 상승여력: **{upside}**

---

## 핵심 이유

**1. {r1t}**
{r1b}

**2. {r2t}**
{r2b}

**3. {r3t}**
{r3b}

---

## 실적 Preview
{m_rows}
---

## 리스크
{risk}

---
*출처: {broker} 리포트 ({date})*
*본 요약은 정보 제공 목적이며 투자 권유가 아닙니다.*
""", encoding="utf-8")

    # shorts-script.md
    (out / "shorts-script.md").write_text(f"""# {name} 쇼츠 스크립트
**예상 시간**: 약 45초
**리포트 출처**: {broker} ({date})

---

## 스크립트

[후크]
"{name} 목표주가 {target} 나왔어요.
{broker} 리포트거든요."

[본론]
"이유 세 가지예요.

첫 번째, {r1t}거든요.
{r1b}

두 번째, {r2t}예요.
{r2b}

세 번째, {r3t}이에요.
{r3b}"

[결론]
"현재 {current}, 목표 {target}.
상승 여력 {upside}예요."

[CTA]
"리포트읽어드림 구독하고 다음 리포트도 받아가세요!"

---

## 화면 구성 제안 (영상 편집용)

| 타임코드 | 화면 | 자막 |
|---------|------|------|
| 0~5초 | {name} + 목표주가 타이포 | "목표주가 {target} ▲" |
| 5~20초 | 실적/이슈 이미지 | "{r1t}" |
| 20~35초 | 핵심 이유 이미지 | "{r2t}" |
| 35~42초 | 목표주가 비교 카드 | "{current} → {target} ({upside})" |
| 42~47초 | 구독 버튼 | "구독하기" |

---

## 영상 설명란

{name}({code}) {broker} 리포트 핵심 정리

현재가: {current}
목표주가: {target} ({upside})
투자의견: {opinion}

⚠️ 투자 권유가 아닌 정보 제공 목적입니다.
출처: {broker} 리포트 ({date})

#{name} #주식 #증권사리포트 #목표주가 #쇼츠

---
*본 영상은 리포트를 읽어드리는 것이며 매수, 매도 추천이 아니며 투자에 대한 책임은 본인에게 있습니다.*
""", encoding="utf-8")

    # thumbnail-prompts.md
    (out / "thumbnail-prompts.md").write_text(f"""# {name} 썸네일 프롬프트

## 쇼츠 썸네일 (1080×1920)

```
Dark navy background (#0D1B2A). Bold Korean stock report thumbnail.
Top: Small white text "{broker}"
Center-top: Large bold white Korean text "{name}"
Center: Huge red bold text "{target}" with upward arrow ✦
Below: White text "목표주가"
Bottom-center: Red bold "{upside}" in large font
Bottom: Small gray text "{opinion} | {r1t}"
Style: Professional Korean financial YouTube Shorts thumbnail. Dark navy background, white and red text only.
```

## 유튜브 썸네일 (1280×720)

```
Dark navy background (#0D1B2A). Korean stock report YouTube thumbnail, landscape.
Left: Large bold white "{name}" with red "{opinion}" badge
Center: Huge red "{target}"
Right: "{upside}" large red with upward arrow
Bottom: White text "{broker} | {r1t}"
```
""", encoding="utf-8")


# ─────────────────────────────────────────
# 산업 리포트 PDF 파싱 및 파일 생성
# ─────────────────────────────────────────

def extract_industry_data(pdf_path: Path) -> dict:
    """PDF를 Gemini로 분석 → 산업 리포트 구조화"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    pdf_bytes = pdf_path.read_bytes()

    prompt = """이 증권사 산업/분야 리포트 PDF에서 다음 정보를 JSON으로 추출해줘.
다른 텍스트 없이 JSON만 출력해줘.

{
  "industry_name": "산업명(예: 반도체, 2차전지, 건설)",
  "report_title": "리포트 제목",
  "broker": "증권사명",
  "date": "발행일(YYYY-MM-DD, 없으면 null)",
  "summary_points": ["핵심포인트1(20자이내)", "핵심포인트2", "핵심포인트3", "핵심포인트4"],
  "current_state": "현재 산업 현황 설명(3-4문장)",
  "trends": [
    {"title": "트렌드1 제목(15자이내)", "body": "설명(2-3문장)"},
    {"title": "트렌드2 제목(15자이내)", "body": "설명(2-3문장)"},
    {"title": "트렌드3 제목(15자이내)", "body": "설명(2-3문장)"}
  ],
  "key_metrics": [
    {"item": "항목명", "value": "수치", "change": "변화"}
  ],
  "outlook": "향후 전망(3-4문장)",
  "investment_points": ["투자포인트1(20자이내)", "투자포인트2", "투자포인트3"],
  "risks": ["리스크1(20자이내)", "리스크2"],
  "conclusion": "핵심 결론(2-3문장)"
}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            prompt,
        ],
    )
    text = response.text.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(m.group() if m else text)


def make_industry_slug(data: dict) -> str:
    industry_map = {
        "반도체": "semiconductor", "2차전지": "battery", "배터리": "battery",
        "건설": "construction", "자동차": "auto", "철강": "steel",
        "화학": "chemical", "바이오": "bio", "헬스케어": "healthcare",
        "금융": "finance", "은행": "bank", "보험": "insurance",
        "소프트웨어": "sw", "게임": "game", "유통": "retail",
        "음식료": "food", "에너지": "energy", "조선": "ship",
        "항공": "airline", "물류": "logistics", "부동산": "realty",
    }
    industry = data.get("industry_name") or "industry"
    raw_date = data.get("date") or ""
    if raw_date.strip() in ("N/A", "n/a", "없음", "미상", "unknown", "-"):
        raw_date = ""
    date = re.sub(r"[^\d]", "", raw_date)
    en = industry_map.get(industry, re.sub(r"[^\w]", "", industry).lower()[:10] or "industry")
    return f"{en}-industry-{date}" if date else f"{en}-industry"


def create_industry_files(slug: str, d: dict):
    out = OUTPUTS_DIR / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / "images").mkdir(exist_ok=True)

    industry = d.get("industry_name") or "산업"
    title    = d.get("report_title") or ""
    broker   = d.get("broker") or ""
    date     = d.get("date") or ""
    summary_points = d.get("summary_points") or []
    current_state  = d.get("current_state") or ""
    trends         = d.get("trends") or []
    metrics        = d.get("key_metrics") or []
    outlook        = d.get("outlook") or ""
    invest_points  = d.get("investment_points") or []
    risks          = d.get("risks") or []
    conclusion     = d.get("conclusion") or ""

    def safe(v):
        return str(v) if v is not None else ""

    trend_md = ""
    for i, t in enumerate(trends[:3]):
        trend_md += f"\n**{i+1}. {safe(t.get('title'))}**\n{safe(t.get('body'))}\n"

    m_rows = "| 항목 | 수치 | 변화 |\n|------|------|------|\n"
    for m in metrics[:8]:
        m_rows += f"| {safe(m.get('item'))} | {safe(m.get('value'))} | {safe(m.get('change'))} |\n"

    (out / "summary.md").write_text(f"""# {industry} 산업 리포트 핵심 요약
- **증권사**: {broker}
- **발행일**: {date}
- **리포트 제목**: {title}

---

## 핵심 요약
{chr(10).join(f'- {p}' for p in summary_points)}

---

## 현황
{current_state}

---

## 주요 트렌드
{trend_md}
---

## 주요 지표
{m_rows}
---

## 전망
{outlook}

---

## 투자 포인트
{chr(10).join(f'- {p}' for p in invest_points)}

---

## 리스크
{chr(10).join(f'- {r}' for r in risks)}

---

## 결론
{conclusion}

---
*출처: {broker} 리포트 ({date})*
*본 요약은 정보 제공 목적이며 투자 권유가 아닙니다.*
""", encoding="utf-8")

    t = [trends[i] if i < len(trends) else {"title": "", "body": ""} for i in range(3)]
    ip = invest_points + [""] * 3
    r  = risks + [""]

    (out / "youtube-script.md").write_text(f"""# {industry} 산업 리포트 롱폼 스크립트
**예상 시간**: 약 7분
**리포트 출처**: {broker} ({date})

---

## 스크립트

[도입]
"안녕하세요, 리포트읽어드림입니다.
오늘은 {broker}에서 발행한 {industry} 산업 리포트를 읽어드릴게요.
{title} 리포트인데요, 핵심만 빠르게 정리해 드릴게요."

[현황]
"먼저 현재 {industry} 산업 현황을 보면요.
{current_state}"

[트렌드1]
"자, 이제 핵심 트렌드 세 가지를 말씀드릴게요.
첫 번째는 {t[0]['title']}입니다.
{t[0]['body']}"

[트렌드2]
"두 번째 트렌드는 {t[1]['title']}예요.
{t[1]['body']}"

[트렌드3]
"세 번째 트렌드는 {t[2]['title']}이에요.
{t[2]['body']}"

[지표]
"주요 수치들도 잠깐 보고 갈게요.
화면에서 핵심 데이터들을 확인해보세요."

[전망]
"그렇다면 앞으로 전망은 어떨까요?
{outlook}"

[투자포인트]
"투자 관점에서 리포트가 짚은 포인트는 세 가지예요.
첫째, {ip[0]}.
둘째, {ip[1]}.
셋째, {ip[2]}."

[결론]
"오늘 {industry} 산업 리포트 핵심만 정리해 드렸는데요.
{conclusion}
리스크도 말씀드리면, {r[0]}{(' 그리고 ' + r[1]) if r[1] else ''}이 있다고 리포트는 지적하고 있어요."

[CTA]
"리포트읽어드림 구독하시면 매주 증권사 리포트 핵심을 이렇게 정리해 드려요.
구독 부탁드리고, 다음 리포트에서 뵙겠습니다!"

---

## 영상 설명란

{industry} 산업 리포트 핵심 정리 | {broker}

{chr(10).join(f'✅ {p}' for p in summary_points)}

⚠️ 투자 권유가 아닌 정보 제공 목적입니다.
출처: {broker} 리포트 ({date})

#{industry} #증권사리포트 #산업분석 #주식 #투자

---
*본 영상은 리포트를 읽어드리는 것이며 매수, 매도 추천이 아니며 투자에 대한 책임은 본인에게 있습니다.*
""", encoding="utf-8")


# ─────────────────────────────────────────
# 백그라운드 처리
# ─────────────────────────────────────────

def process_job(job_id: str, image_path: Path):
    try:
        is_pdf = image_path.suffix.lower() == ".pdf"

        if is_pdf:
            # ── 산업 리포트 롱폼 파이프라인 ──
            jobs[job_id].update({"step": 1, "message": "📊 산업 리포트 분석 중... (약 20초)"})
            data = extract_industry_data(image_path)
            slug = make_industry_slug(data)
            industry = data.get("industry_name") or slug

            jobs[job_id].update({"step": 2, "message": f"📝 {industry} 콘텐츠 파일 생성 중..."})
            create_industry_files(slug, data)

            jobs[job_id].update({"step": 3, "message": "🎬 슬라이드·음성·영상 생성 중... (약 3분)"})
            result = subprocess.run(
                ["python3", str(BASE_DIR / "scripts" / "produce.py"), slug, "industry"],
                capture_output=True, text=True, cwd=str(BASE_DIR),
            )
        else:
            # ── 종목 리포트 쇼츠 파이프라인 ──
            jobs[job_id].update({"step": 1, "message": "📊 리포트 분석 중... (약 10초)"})
            data = extract_report_data(image_path)
            slug = make_slug(data)
            stock = data.get("stock_name") or slug

            jobs[job_id].update({"step": 2, "message": f"📝 {stock} 콘텐츠 파일 생성 중..."})
            create_content_files(slug, data)

            jobs[job_id].update({"step": 3, "message": "🎬 이미지·음성·영상 생성 중... (약 1분)"})
            result = subprocess.run(
                ["python3", str(BASE_DIR / "scripts" / "produce.py"), slug, "shorts"],
                capture_output=True, text=True, cwd=str(BASE_DIR),
            )

        if result.returncode != 0:
            err = (result.stderr or result.stdout or "알 수 없는 오류")[-400:]
            raise RuntimeError(err)

        jobs[job_id].update({
            "status": "complete",
            "step": 4,
            "message": f"✅ 완료! Outputs/{slug} 폴더를 확인하세요.",
            "slug": slug,
        })

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[ERROR] {tb}")
        jobs[job_id].update({"status": "error", "message": f"❌ 오류: {str(e)[:300]}\n{tb[-500:]}"})


# ─────────────────────────────────────────
# Flask 라우트
# ─────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "파일이 없어요"}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".pdf"}:
        return jsonify({"error": "PNG, JPG, PDF만 가능해요"}), 400

    job_id = str(uuid.uuid4())[:8]
    save_path = UPLOADS_DIR / f"{job_id}{ext}"
    file.save(str(save_path))

    jobs[job_id] = {"status": "processing", "step": 0, "message": "⏳ 시작 중..."}
    threading.Thread(target=process_job, args=(job_id, save_path), daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    return jsonify(jobs.get(job_id, {"status": "unknown", "message": "알 수 없는 작업"}))


@app.route("/open/<slug>")
def open_folder(slug):
    subprocess.Popen(["open", str(OUTPUTS_DIR / slug)])
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("🚀 리포트읽어드림 대시보드 시작!")
    print("📱 브라우저: http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
