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
# 백그라운드 처리
# ─────────────────────────────────────────

def process_job(job_id: str, image_path: Path):
    try:
        jobs[job_id].update({"step": 1, "message": "📊 리포트 분석 중... (약 10초)"})
        data = extract_report_data(image_path)
        slug = make_slug(data)
        stock = data.get("stock_name", slug)

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
