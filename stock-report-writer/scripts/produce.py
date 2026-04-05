"""
리포트읽어드림 - 영상 자동 제작 스크립트
Usage:
    python3 scripts/produce.py <slug> [shorts|youtube]
    python3 scripts/produce.py semco-20260403 shorts
    python3 scripts/produce.py daedeok-20260401 youtube
"""

import os
import sys
import re
import io
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드 (스크립트 위치 기준)
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

OUTPUTS_DIR = BASE_DIR / "Outputs"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google Cloud TTS 인증 - 절대 경로로 변환
gac = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
if gac and not os.path.isabs(gac):
    abs_gac = str(BASE_DIR / gac.lstrip("./"))
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_gac


# ─────────────────────────────────────────
# Step 1: 이미지 생성 (PIL - summary.md 기반)
# ─────────────────────────────────────────

def _load_font(size: int, bold: bool = False):
    """macOS 한국어 폰트 로드"""
    from PIL import ImageFont
    candidates = [
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 1 if bold else 0),
        ("/System/Library/Fonts/Supplemental/AppleGothic.ttf", 0),
        ("/Library/Fonts/NanumGothicBold.ttf" if bold else "/Library/Fonts/NanumGothic.ttf", 0),
    ]
    for path, idx in candidates:
        try:
            return ImageFont.truetype(path, size, index=idx)
        except Exception:
            continue
    return ImageFont.load_default()


def _rounded_rect(draw, xy, radius, fill):
    """모서리가 둥근 사각형"""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    for cx, cy in [(x1, y1), (x2 - 2*radius, y1), (x1, y2 - 2*radius), (x2 - 2*radius, y2 - 2*radius)]:
        draw.ellipse([cx, cy, cx + 2*radius, cy + 2*radius], fill=fill)


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """텍스트를 max_chars 기준으로 줄바꿈"""
    if len(text) <= max_chars:
        return [text]
    # 공백 기준 자르기 시도
    mid = len(text) // 2
    split = text.rfind(' ', 0, mid + 5)
    if split == -1:
        split = mid
    return [text[:split].strip(), text[split:].strip()]


def generate_images(slug: str):
    """summary.md 데이터를 PIL로 렌더링 → 한국어 정확한 인포그래픽 카드 3장"""
    from PIL import Image, ImageDraw

    summary_file = OUTPUTS_DIR / slug / "summary.md"
    if not summary_file.exists():
        print(f"⚠️  summary.md 없음: {summary_file}")
        return []

    content = summary_file.read_text(encoding="utf-8")

    # ── 데이터 파싱 ──
    def extract(pattern, default=""):
        m = re.search(pattern, content)
        return m.group(1).strip() if m else default

    title_m = re.search(r'^# (.+?) \(', content, re.MULTILINE)
    stock_name = title_m.group(1) if title_m else slug

    broker   = extract(r'\*\*증권사\*\*[^:]*:\s*\**([^(\n\*]+)', "증권사")
    opinion  = extract(r'\*\*투자의견\*\*:\s*(\w+)', "BUY")
    cur_price = extract(r'현재가[^:\n]*:\s*\*\*([^\*\n]+)\*\*', "")
    tgt_price = extract(r'- 목표주가:\s*\*\*([^\*\n]+)\*\*', "")
    upside   = extract(r'상승여력[^:]*:\s*\*\*([^\*\n]+)\*\*', "")

    # 핵심 이유 제목 (볼드 숫자 뒤 텍스트)
    reasons = re.findall(r'\*\*\d+\.\s*(.+?)\*\*', content)

    # 실적 테이블
    table_rows = re.findall(
        r'\|\s*([^|\-][^|]*?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|',
        content
    )
    metrics = [
        (r[0].strip(), r[1].strip(), r[2].strip())
        for r in table_rows
        if r[0].strip() not in ('항목', '---', '----', '')
    ]

    images_dir = OUTPUTS_DIR / slug / "images"
    images_dir.mkdir(exist_ok=True)

    # ── 색상 팔레트 ──
    BG       = (13,  27,  42)
    WHITE    = (255, 255, 255)
    RED      = (220,  38,  38)
    GRAY     = (160, 170, 185)
    CARD_BG  = (22,  42,  62)
    GREEN    = (34,  197,  94)
    BLUE     = (59,  130, 246)

    W, H = 1080, 1920
    image_paths = []

    # ════════════════════════════════
    # 카드 1: 목표주가
    # ════════════════════════════════
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)

    d.text((W//2, 110), "리포트읽어드림", font=_load_font(38), fill=GRAY, anchor="mm")
    d.text((W//2, 195), broker.strip(), font=_load_font(44), fill=GRAY, anchor="mm")

    d.text((W//2, 380), stock_name, font=_load_font(108, bold=True), fill=WHITE, anchor="mm")

    # BUY 배지
    bw, bh = 180, 64
    bx, by = W//2 - bw//2, 470
    _rounded_rect(d, (bx, by, bx+bw, by+bh), 32, RED)
    d.text((W//2, by+bh//2), opinion, font=_load_font(46, bold=True), fill=WHITE, anchor="mm")

    d.line([(80, 590), (W-80, 590)], fill=(40, 60, 80), width=2)

    d.text((W//2, 680), "현재가", font=_load_font(46), fill=GRAY, anchor="mm")
    d.text((W//2, 775), cur_price, font=_load_font(68, bold=True), fill=WHITE, anchor="mm")
    d.text((W//2, 870), "▼", font=_load_font(52), fill=GRAY, anchor="mm")
    d.text((W//2, 970), "목표주가", font=_load_font(46), fill=GRAY, anchor="mm")
    d.text((W//2, 1100), tgt_price, font=_load_font(116, bold=True), fill=RED, anchor="mm")

    d.line([(80, 1180), (W-80, 1180)], fill=(40, 60, 80), width=2)

    d.text((W//2, 1290), f"상승여력  {upside}", font=_load_font(80, bold=True), fill=RED, anchor="mm")

    d.text((W//2, 1870), f"출처: {broker.strip()}", font=_load_font(36), fill=GRAY, anchor="mm")

    out = images_dir / f"{slug}-img-01.png"
    img.save(str(out))
    image_paths.append(out)
    print(f"  ✅ 저장: {out.name}")

    # ════════════════════════════════
    # 카드 2: 핵심 이유 3가지
    # ════════════════════════════════
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)

    d.text((W//2, 110), "목표주가 상향 이유", font=_load_font(50), fill=GRAY, anchor="mm")
    d.text((W//2, 230), "핵심 3가지", font=_load_font(100, bold=True), fill=WHITE, anchor="mm")

    card_y = 370
    num_colors = [RED, GREEN, BLUE]
    num_labels = ["①", "②", "③"]

    for i, reason in enumerate(reasons[:3]):
        card_h = 200
        _rounded_rect(d, (60, card_y, W-60, card_y+card_h), 20, CARD_BG)

        d.text((130, card_y+card_h//2), num_labels[i],
               font=_load_font(64, bold=True), fill=num_colors[i], anchor="mm")

        lines = _wrap_text(reason, 14)
        if len(lines) == 1:
            d.text((200, card_y+card_h//2), lines[0],
                   font=_load_font(46, bold=True), fill=WHITE, anchor="lm")
        else:
            d.text((200, card_y+card_h//2 - 30), lines[0],
                   font=_load_font(44, bold=True), fill=WHITE, anchor="lm")
            d.text((200, card_y+card_h//2 + 30), lines[1],
                   font=_load_font(44, bold=True), fill=GRAY, anchor="lm")

        card_y += card_h + 30

    # 목표주가 요약
    sum_y = card_y + 40
    d.text((W//2, sum_y), f"목표주가  {tgt_price}",
           font=_load_font(66, bold=True), fill=RED, anchor="mm")
    d.text((W//2, sum_y+90), f"상승여력  {upside}",
           font=_load_font(54), fill=RED, anchor="mm")

    d.text((W//2, 1870), f"출처: {broker.strip()}", font=_load_font(36), fill=GRAY, anchor="mm")

    out = images_dir / f"{slug}-img-02.png"
    img.save(str(out))
    image_paths.append(out)
    print(f"  ✅ 저장: {out.name}")

    # ════════════════════════════════
    # 카드 3: 실적 하이라이트
    # ════════════════════════════════
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)

    d.text((W//2, 120), stock_name, font=_load_font(86, bold=True), fill=WHITE, anchor="mm")
    d.text((W//2, 240), "1분기 실적 Preview", font=_load_font(52), fill=GRAY, anchor="mm")
    d.line([(80, 310), (W-80, 310)], fill=(40, 60, 80), width=2)

    row_y = 360
    for item, val, change in metrics[:6]:
        rh = 150
        _rounded_rect(d, (60, row_y, W-60, row_y+rh), 16, CARD_BG)
        d.text((110, row_y+rh//2), item,
               font=_load_font(42), fill=GRAY, anchor="lm")
        d.text((W-110, row_y+rh//2 - 22), val,
               font=_load_font(50, bold=True), fill=WHITE, anchor="rm")
        c_color = RED if "+" in change else GRAY
        d.text((W-110, row_y+rh//2 + 28), change,
               font=_load_font(38), fill=c_color, anchor="rm")
        row_y += rh + 20

    d.text((W//2, 1870), f"출처: {broker.strip()}", font=_load_font(36), fill=GRAY, anchor="mm")

    out = images_dir / f"{slug}-img-03.png"
    img.save(str(out))
    image_paths.append(out)
    print(f"  ✅ 저장: {out.name}")

    return image_paths


# ─────────────────────────────────────────
# Step 2: 썸네일 생성 (Gemini API)
# ─────────────────────────────────────────

def generate_thumbnails(slug: str, video_type: str = "shorts"):
    """thumbnail-prompts.md로 썸네일 생성"""
    from google import genai
    from google.genai import types
    from PIL import Image

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompts_file = OUTPUTS_DIR / slug / "thumbnail-prompts.md"
    if not prompts_file.exists():
        print(f"⚠️  thumbnail-prompts.md 없음")
        return

    content = prompts_file.read_text(encoding="utf-8")
    prompts = re.findall(r"```\n(.*?)\n```", content, re.DOTALL)
    names = ["thumbnail-shorts.png", "thumbnail-youtube.png"]

    for i, (prompt, name) in enumerate(zip(prompts, names)):
        if video_type == "shorts" and i == 1:
            continue
        if video_type == "youtube" and i == 0:
            continue

        print(f"  썸네일 생성 중: {name}")
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=prompt.strip(),
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"]
                ),
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    img = Image.open(io.BytesIO(part.inline_data.data))
                    out_path = OUTPUTS_DIR / slug / name
                    img.save(str(out_path))
                    print(f"  ✅ 저장: {out_path.name}")
                    break
        except Exception as e:
            print(f"  ❌ 썸네일 실패: {e}")


# ─────────────────────────────────────────
# Step 3: 음성 생성 (Google Cloud TTS)
# ─────────────────────────────────────────

def extract_narration(script_md: str) -> str:
    """스크립트에서 나레이션 텍스트만 추출"""
    lines = script_md.split("\n")
    narration = []
    in_script = False

    for line in lines:
        if "## 스크립트" in line:
            in_script = True
            continue
        if in_script and line.startswith("## "):
            break
        if not in_script:
            continue

        line = re.sub(r"\[.*?\]", "", line)   # 지문 제거
        line = line.strip().strip('"').strip("*").strip("#").strip("━")
        if "|" in line:
            continue
        if line:
            narration.append(line)

    text = " ".join(narration)
    text += " 본 영상은 리포트를 읽어드리는 것이며 매수, 매도 추천이 아니며 투자에 대한 책임은 본인에게 있습니다."
    return text


def generate_audio(slug: str, video_type: str = "shorts"):
    """Google Cloud TTS로 한국어 음성 생성"""
    from google.cloud import texttospeech

    script_file = OUTPUTS_DIR / slug / f"{video_type}-script.md"
    if not script_file.exists():
        print(f"⚠️  스크립트 없음: {script_file}")
        return None

    narration = extract_narration(script_file.read_text(encoding="utf-8"))
    print(f"  나레이션 길이: {len(narration)}자")

    client = texttospeech.TextToSpeechClient()
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=narration),
        voice=texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            name="ko-KR-Neural2-C",   # 남성 / 여성: ko-KR-Neural2-A
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.1,
        ),
    )

    audio_path = OUTPUTS_DIR / slug / f"audio-{video_type}.mp3"
    audio_path.write_bytes(response.audio_content)
    print(f"  ✅ 음성 저장: {audio_path.name}")
    return audio_path


# ─────────────────────────────────────────
# Step 4: 영상 조합 (MoviePy)
# ─────────────────────────────────────────

def extract_section_weights(script_md: str, n_images: int) -> list:
    """[후크]/[본론]/[결론]/[CTA] 마커 기반으로 이미지 표시 비율 계산"""
    # 마커로 섹션 분리
    parts = re.split(r'\[([^\]]+)\]', script_md)
    # parts = ['앞부분', '마커', '내용', '마커', '내용', ...]

    sections = []
    for i in range(1, len(parts) - 1, 2):
        marker = parts[i].strip()
        text = parts[i + 1] if i + 1 < len(parts) else ""
        # 헤더/테이블/따옴표 제거하고 순수 나레이션만
        text = re.sub(r'^\s*#.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\|.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'["""\'*]', '', text).strip()
        if text:
            sections.append((marker, text))

    if not sections:
        return [1.0 / n_images] * n_images

    # 섹션을 n_images 그룹으로 묶기 (앞에서 1개씩, 나머지 마지막으로)
    per = max(1, len(sections) // n_images)
    groups = []
    for i in range(n_images):
        start = i * per
        end = start + per if i < n_images - 1 else len(sections)
        text = " ".join(v for _, v in sections[start:end])
        groups.append(max(len(text), 1))

    total = sum(groups)
    return [g / total for g in groups]


def generate_video(slug: str, video_type: str = "shorts"):
    """이미지 + 음성 → mp4 조합"""
    from moviepy.editor import (
        ImageClip, AudioFileClip, concatenate_videoclips,
        CompositeVideoClip, ColorClip,
    )

    audio_path = OUTPUTS_DIR / slug / f"audio-{video_type}.mp3"
    images_dir = OUTPUTS_DIR / slug / "images"
    output_path = OUTPUTS_DIR / slug / f"{video_type}-video.mp4"

    if not audio_path.exists():
        print("⚠️  음성 파일 없음")
        return

    size = (1080, 1920) if video_type == "shorts" else (1920, 1080)

    image_files = sorted(images_dir.glob(f"{slug}-img-*.png"))
    if not image_files:
        thumb = OUTPUTS_DIR / slug / f"thumbnail-{video_type}.png"
        image_files = [thumb] if thumb.exists() else []
    if not image_files:
        print("❌ 사용할 이미지 없음")
        return

    audio = AudioFileClip(str(audio_path))
    n = len(image_files)
    FADE = 0.6  # 크로스페이드 길이(초)

    DISC_DUR = 4  # 면책 카드 길이(초)
    # 크로스페이드 오버랩을 고려한 총 이미지 시간
    # 총 영상 = sum(이미지) + DISC_DUR - n*FADE  →  sum(이미지) = audio - DISC_DUR + n*FADE
    total_img_time = max(audio.duration - DISC_DUR + n * FADE, n * 2.0)

    # 스크립트 섹션 길이로 이미지별 가중치 계산
    script_file = OUTPUTS_DIR / slug / f"{video_type}-script.md"
    if script_file.exists() and n > 1:
        weights = extract_section_weights(script_file.read_text(encoding="utf-8"), n)
        durations = [max(total_img_time * w, 1.5) for w in weights]
    else:
        durations = [total_img_time / n] * n

    print(f"  영상 길이: {audio.duration:.1f}초 / 이미지 {n}개")
    print(f"  장면 길이: {' / '.join(f'{d:.1f}s' for d in durations)}")

    clips = []
    for i, (img_path, dur) in enumerate(zip(image_files, durations)):
        clip = ImageClip(str(img_path)).set_duration(dur).resize(size)
        if i > 0:
            clip = clip.crossfadein(FADE)
        clips.append(clip)

    # 면책 카드 (마지막 3초) - PIL 카드 스타일
    from PIL import Image as PILImage, ImageDraw as PILDraw
    import numpy as np

    BG_C  = (13, 27, 42)
    CARD_C = (22, 42, 62)
    W_d, H_d = size

    disc_img = PILImage.new('RGB', (W_d, H_d), BG_C)
    dd = PILDraw.Draw(disc_img)

    # 채널명
    dd.text((W_d//2, H_d//2 - 220), "리포트읽어드림",
            font=_load_font(52), fill=(160, 170, 185), anchor="mm")

    # 구분선
    dd.line([(80, H_d//2 - 160), (W_d - 80, H_d//2 - 160)], fill=(40, 60, 80), width=2)

    # 면책 카드 배경
    _rounded_rect(dd, (60, H_d//2 - 130, W_d - 60, H_d//2 + 130), 20, CARD_C)

    disc_lines = [
        "본 영상은 리포트를 읽어드리는 것이며",
        "매수, 매도 추천이 아니며",
        "투자에 대한 책임은 본인에게 있습니다",
    ]
    for j, line in enumerate(disc_lines):
        dd.text((W_d//2, H_d//2 - 60 + j * 70), line,
                font=_load_font(44), fill=(255, 255, 255), anchor="mm")

    # 구독 CTA
    dd.line([(80, H_d//2 + 160), (W_d - 80, H_d//2 + 160)], fill=(40, 60, 80), width=2)
    dd.text((W_d//2, H_d//2 + 230), "구독하고 다음 리포트도 받아가세요!",
            font=_load_font(42), fill=(220, 38, 38), anchor="mm")

    disc_clip = ImageClip(np.array(disc_img)).set_duration(DISC_DUR).crossfadein(FADE)
    clips.append(disc_clip)

    video = concatenate_videoclips(clips, padding=-FADE, method="compose")
    video = video.set_audio(audio.set_duration(video.duration))
    video.write_videofile(str(output_path), fps=24, codec="libx264",
                          audio_codec="aac", threads=4, logger=None)
    print(f"  ✅ 영상 저장: {output_path.name}")


# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────

def produce(slug: str, video_type: str = "shorts"):
    out_dir = OUTPUTS_DIR / slug
    if not out_dir.exists():
        available = [d.name for d in OUTPUTS_DIR.iterdir() if d.is_dir()]
        print(f"❌ 슬러그 없음: {slug}")
        print(f"   사용 가능: {available}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"🎬  리포트읽어드림 영상 제작")
    print(f"    종목: {slug}  |  타입: {video_type}")
    print(f"{'='*50}")

    print("\n[1/4] 이미지 생성 중...")
    generate_images(slug)

    print("\n[2/4] 썸네일 생성 중...")
    generate_thumbnails(slug, video_type)

    print("\n[3/4] 음성 생성 중...")
    generate_audio(slug, video_type)

    print("\n[4/4] 영상 조합 중...")
    generate_video(slug, video_type)

    print(f"\n🎉 완료! → Outputs/{slug}/{video_type}-video.mp4")
    print("유튜브 업로드만 하면 끝이에요!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/produce.py <slug> [shorts|youtube]")
        sys.exit(1)

    produce(
        slug=sys.argv[1],
        video_type=sys.argv[2] if len(sys.argv) > 2 else "shorts",
    )
