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

    # 실적 테이블 - 라인별 파싱 (정규식보다 안정적)
    metrics = []
    for line in content.split('\n'):
        line = line.strip()
        if not line.startswith('|') or '---' in line:
            continue
        parts = [p.strip() for p in line.strip('|').split('|')]
        if len(parts) < 3 or parts[0] in ('항목', '타임코드', ''):
            continue
        metrics.append((parts[0], parts[1], parts[2]))

    images_dir = OUTPUTS_DIR / slug / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

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

def extract_narration(script_md: str, is_term: bool = False) -> str:
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
    if is_term:
        text += " 본 영상은 정보 제공 목적이며 투자 권유가 아닙니다."
    else:
        text += " 본 영상은 리포트를 읽어드리는 것이며 매수, 매도 추천이 아니며 투자에 대한 책임은 본인에게 있습니다."
    return text


def generate_audio(slug: str, video_type: str = "shorts", is_term: bool = False):
    """Google Cloud TTS로 한국어 음성 생성"""
    from google.cloud import texttospeech

    script_file = OUTPUTS_DIR / slug / f"{video_type}-script.md"
    if not script_file.exists():
        print(f"⚠️  스크립트 없음: {script_file}")
        return None

    narration = extract_narration(script_file.read_text(encoding="utf-8"), is_term=is_term)
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
            speaking_rate=0.95 if is_term else 1.1,
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
    # ## 스크립트 섹션만 추출 (--- 또는 다음 ## 이전까지)
    script_section = ""
    in_script = False
    for line in script_md.split('\n'):
        if '## 스크립트' in line:
            in_script = True
            continue
        if in_script and (line.startswith('## ') or line.strip() == '---'):
            break
        if in_script:
            script_section += line + '\n'

    if not script_section.strip():
        return [1.0 / n_images] * n_images

    # 마커로 섹션 분리
    parts = re.split(r'\[([^\]]+)\]', script_section)

    sections = []
    for i in range(1, len(parts) - 1, 2):
        text = parts[i + 1] if i + 1 < len(parts) else ""
        text = re.sub(r'["""\'*]', '', text).strip()
        if text:
            sections.append(text)

    if not sections:
        return [1.0 / n_images] * n_images

    per = max(1, len(sections) // n_images)
    groups = []
    for i in range(n_images):
        start = i * per
        end = start + per if i < n_images - 1 else len(sections)
        groups.append(max(sum(len(s) for s in sections[start:end]), 1))

    total = sum(groups)
    return [g / total for g in groups]


def generate_video(slug: str, video_type: str = "shorts", is_term: bool = False):
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
    FADE = 1.2 if is_term else 0.6  # 크로스페이드 길이(초)

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

    if is_term:
        disc_lines = [
            "본 영상은 정보 제공 목적이며",
            "투자 권유가 아닙니다",
        ]
    else:
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
    cta_text = "구독하고 다음 용어도 배워가세요!" if is_term else "구독하고 다음 리포트도 받아가세요!"
    dd.text((W_d//2, H_d//2 + 230), cta_text,
            font=_load_font(42), fill=(220, 38, 38), anchor="mm")

    disc_clip = ImageClip(np.array(disc_img)).set_duration(DISC_DUR).crossfadein(FADE)
    clips.append(disc_clip)

    video = concatenate_videoclips(clips, padding=-FADE, method="compose")
    video = video.set_audio(audio.set_duration(video.duration))
    video.write_videofile(str(output_path), fps=24, codec="libx264",
                          audio_codec="aac", threads=4, logger=None)
    print(f"  ✅ 영상 저장: {output_path.name}")


# ─────────────────────────────────────────
# Step 1c: 경제 용어 카드 생성 (1080x1920)
# ─────────────────────────────────────────

def generate_term_images(slug: str) -> list:
    """경제 용어 카드 4장 생성 - BUGI 스타일 (따뜻한 오렌지/베이지)"""
    from PIL import Image, ImageDraw

    summary_file = OUTPUTS_DIR / slug / "summary.md"
    if not summary_file.exists():
        print(f"⚠️  summary.md 없음: {summary_file}")
        return []

    content = summary_file.read_text(encoding="utf-8")

    def ex(pattern, default=""):
        m = re.search(pattern, content)
        return m.group(1).strip() if m else default

    term        = content.split('\n')[0].replace('# ', '').split(' 경제')[0].strip()
    english     = ex(r'\*\*영어\*\*:\s*([^\n]+)', "")
    one_line    = ex(r'\*\*한 줄 요약\*\*:\s*([^\n]+)', "")
    why_know    = _parse_section(content, "왜 알아야 할까요").replace('\n', ' ')
    what_means  = _parse_section(content, "무슨 뜻인가요").replace('\n', ' ')
    analogy     = _parse_section(content, "쉬운 비유").replace('\n', ' ')
    money_items = _parse_bullets(_parse_section(content, "내 돈에 미치는 영향"))
    key_items   = _parse_bullets(_parse_section(content, "핵심 요약"))
    catchphrase = ex(r'\*\*슬로건\*\*:\s*([^\n]+)', "")

    images_dir = OUTPUTS_DIR / slug / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    WARM_BG   = (255, 248, 238)
    DARK      = (30,  30,  50)
    ORANGE    = (234, 88,  12)
    LIGHT_ORG = (254, 215, 170)
    WHITE     = (255, 255, 255)
    GRAY      = (107, 114, 128)
    DARK_GRAY = (55,  65,  81)

    W, H = 1080, 1920
    image_paths = []

    def save_card(img, idx):
        out = images_dir / f"{slug}-img-{idx:02d}.png"
        img.save(str(out))
        image_paths.append(out)
        print(f"  ✅ 카드 {idx}: {out.name}")

    def orange_header(d, txt="경제 용어 한방 정리"):
        d.rectangle([0, 0, W, 120], fill=ORANGE)
        d.text((W // 2, 60), txt, font=_load_font(40, bold=True), fill=WHITE, anchor="mm")

    def bottom_bar(d, txt="구독하고 다음 용어도 알아가세요!"):
        d.rectangle([0, H - 100, W, H], fill=DARK)
        d.text((W // 2, H - 50), txt, font=_load_font(34), fill=WHITE, anchor="mm")

    def section_label(d, y, txt, color=None):
        """섹션 라벨 (이모지 없이 텍스트만)"""
        c = color or ORANGE
        d.text((80, y), txt, font=_load_font(46, bold=True), fill=c, anchor="lm")
        return y + 60

    # ══ 카드 1: 한 줄 요약 + 왜 알아야 할까요? ══
    img = Image.new('RGB', (W, H), WARM_BG)
    d = ImageDraw.Draw(img)
    orange_header(d)

    d.text((W // 2, 265), term, font=_load_font(110, bold=True), fill=DARK, anchor="mm")
    if english:
        d.text((W // 2, 370), f"({english})", font=_load_font(42), fill=GRAY, anchor="mm")

    # 한 줄 요약 박스 (오렌지) - 동적 높이
    ol_lines = _wrap(one_line, 20)[:2]
    box_h = 100 + len(ol_lines) * 52
    _rounded_rect(d, (60, 415, W - 60, 415 + box_h), 20, ORANGE)
    d.text((W // 2, 448), "한 줄 요약", font=_load_font(32, bold=True), fill=LIGHT_ORG, anchor="mm")
    for i, ln in enumerate(ol_lines):
        d.text((W // 2, 498 + i * 52), ln, font=_load_font(42, bold=True), fill=WHITE, anchor="mm")

    sep_y = 415 + box_h + 30
    d.line([(60, sep_y), (W - 60, sep_y)], fill=LIGHT_ORG, width=3)

    label_y = sep_y + 60
    d.text((80, label_y), "왜 알아야 할까요?", font=_load_font(46, bold=True), fill=ORANGE, anchor="lm")
    card_y = label_y + 60
    _rounded_rect(d, (60, card_y, W - 60, card_y + 280), 20, WHITE)
    for i, ln in enumerate(_wrap(why_know, 19)[:4]):
        d.text((W // 2, card_y + 58 + i * 68), ln, font=_load_font(42), fill=DARK_GRAY, anchor="mm")

    bottom_bar(d)
    save_card(img, 1)

    # ══ 카드 2: 무슨 뜻인가요? ══
    img = Image.new('RGB', (W, H), WARM_BG)
    d = ImageDraw.Draw(img)
    orange_header(d)

    d.text((W // 2, 220), term, font=_load_font(80, bold=True), fill=DARK, anchor="mm")
    d.text((W // 2, 310), "무슨 뜻인가요?", font=_load_font(52, bold=True), fill=ORANGE, anchor="mm")
    d.line([(60, 365), (W - 60, 365)], fill=LIGHT_ORG, width=3)

    # 쉬운 설명 카드 - 최대 4줄 고정
    wm_lines = _wrap(what_means, 19)[:4]
    wm_h = 80 + len(wm_lines) * 68
    _rounded_rect(d, (60, 395, W - 60, 395 + wm_h), 22, WHITE)
    for i, ln in enumerate(wm_lines):
        d.text((W // 2, 455 + i * 68), ln, font=_load_font(42), fill=DARK_GRAY, anchor="mm")

    # 비유 카드 - 최대 4줄 고정
    an_start = 395 + wm_h + 30
    d.text((80, an_start + 44), "쉽게 비유하면요", font=_load_font(44, bold=True), fill=ORANGE, anchor="lm")
    an_card_y = an_start + 100
    an_lines = _wrap(analogy, 19)[:4]
    an_h = 70 + len(an_lines) * 66
    _rounded_rect(d, (60, an_card_y, W - 60, an_card_y + an_h), 22, LIGHT_ORG)
    d.line([(100, an_card_y + 10), (W - 100, an_card_y + 10)], fill=ORANGE, width=2)
    for i, ln in enumerate(an_lines):
        d.text((W // 2, an_card_y + 55 + i * 66), ln, font=_load_font(42), fill=DARK, anchor="mm")

    bottom_bar(d)
    save_card(img, 2)

    # ══ 카드 3: 내 돈에 미치는 영향 ══
    img = Image.new('RGB', (W, H), WARM_BG)
    d = ImageDraw.Draw(img)
    orange_header(d)

    d.text((W // 2, 220), term, font=_load_font(80, bold=True), fill=DARK, anchor="mm")
    d.text((W // 2, 315), "내 돈에 미치는 영향", font=_load_font(52, bold=True), fill=ORANGE, anchor="mm")
    d.line([(60, 370), (W - 60, 370)], fill=LIGHT_ORG, width=3)

    imp_y = 410
    for item in money_items[:3]:
        mi_lines = _wrap(item, 17)[:3]
        rh = 60 + len(mi_lines) * 60
        _rounded_rect(d, (60, imp_y, W - 60, imp_y + rh), 20, WHITE)
        d.text((118, imp_y + rh // 2), "▶", font=_load_font(44, bold=True), fill=ORANGE, anchor="mm")
        d.line([(158, imp_y + 18), (158, imp_y + rh - 18)], fill=LIGHT_ORG, width=2)
        for j, ln in enumerate(mi_lines):
            d.text((188, imp_y + 35 + j * 60), ln,
                   font=_load_font(40, bold=True if j == 0 else False),
                   fill=(DARK if j == 0 else DARK_GRAY), anchor="lm")
        imp_y += rh + 22

    # 슬로건
    if catchphrase:
        cp_lines = _wrap(catchphrase, 20)[:2]
        cp_h = 60 + len(cp_lines) * 56
        _rounded_rect(d, (60, imp_y + 20, W - 60, imp_y + 20 + cp_h), 30, ORANGE)
        for i, ln in enumerate(cp_lines):
            d.text((W // 2, imp_y + 55 + i * 56), f'"{ln}"' if i == 0 else ln,
                   font=_load_font(44, bold=True), fill=WHITE, anchor="mm")

    bottom_bar(d)
    save_card(img, 3)

    # ══ 카드 4: 핵심 요약 ══
    img = Image.new('RGB', (W, H), WARM_BG)
    d = ImageDraw.Draw(img)
    orange_header(d, "핵심 요약")

    d.text((W // 2, 220), term, font=_load_font(80, bold=True), fill=DARK, anchor="mm")
    d.text((W // 2, 318), "이것만 기억하세요!", font=_load_font(48), fill=GRAY, anchor="mm")
    d.line([(60, 375), (W - 60, 375)], fill=LIGHT_ORG, width=3)

    ky = 410
    for i, item in enumerate(key_items[:3]):
        ki_lines = _wrap(item, 16)[:3]
        rh = 60 + len(ki_lines) * 62
        _rounded_rect(d, (60, ky, W - 60, ky + rh), 20, WHITE)
        _rounded_rect(d, (74, ky + rh // 2 - 40, 154, ky + rh // 2 + 40), 40, ORANGE)
        d.text((114, ky + rh // 2), str(i + 1), font=_load_font(50, bold=True), fill=WHITE, anchor="mm")
        for j, ln in enumerate(ki_lines):
            d.text((180, ky + 34 + j * 62), ln,
                   font=_load_font(40, bold=True if j == 0 else False),
                   fill=(DARK if j == 0 else DARK_GRAY), anchor="lm")
        ky += rh + 20

    # 슬로건
    if catchphrase:
        cp_lines = _wrap(catchphrase, 20)[:2]
        cp_h = 60 + len(cp_lines) * 56
        _rounded_rect(d, (60, ky + 20, W - 60, ky + 20 + cp_h), 30, ORANGE)
        for i, ln in enumerate(cp_lines):
            d.text((W // 2, ky + 55 + i * 56), f'"{ln}"' if i == 0 else ln,
                   font=_load_font(44, bold=True), fill=WHITE, anchor="mm")

    bottom_bar(d, "구독하고 다음 경제 용어도 알아가세요!")
    save_card(img, 4)

    return image_paths


def produce_term(slug: str):
    """경제 용어 쇼츠 파이프라인"""
    out_dir = OUTPUTS_DIR / slug
    if not out_dir.exists():
        print(f"❌ 슬러그 없음: {slug}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"💡  리포트읽어드림 경제 용어 쇼츠")
    print(f"    슬러그: {slug}")
    print(f"{'='*50}")

    print("\n[1/3] 카드 생성 중...")
    generate_term_images(slug)

    print("\n[2/3] 음성 생성 중...")
    generate_audio(slug, "shorts", is_term=True)

    print("\n[3/3] 영상 조합 중...")
    generate_video(slug, "shorts", is_term=True)

    print(f"\n🎉 완료! → Outputs/{slug}/shorts-video.mp4")


# ─────────────────────────────────────────
# Step 1b: 산업 리포트 슬라이드 생성 (1920x1080)
# ─────────────────────────────────────────

def _parse_section(content: str, heading: str) -> str:
    """## heading 섹션 텍스트 추출"""
    in_section = False
    lines = []
    for line in content.split('\n'):
        if f'## {heading}' in line:
            in_section = True
            continue
        if in_section and line.startswith('## '):
            break
        if in_section:
            lines.append(line)
    return '\n'.join(lines).strip()


def _parse_bullets(text: str) -> list:
    """- 항목 리스트 추출"""
    items = []
    for line in text.split('\n'):
        line = line.strip().lstrip('- ').strip()
        if line and not line.startswith('#') and not line.startswith('|') and not line.startswith('*출처'):
            items.append(line)
    return items


def _wrap(text: str, max_chars: int) -> list:
    """한국어 텍스트 줄바꿈 (max_chars 기준)"""
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    lines = []
    while len(text) > max_chars:
        sp = text.rfind(' ', 0, max_chars + 4)
        if sp == -1:
            sp = max_chars
        lines.append(text[:sp].strip())
        text = text[sp:].strip()
    if text:
        lines.append(text)
    return lines


def generate_industry_images(slug: str) -> list:
    """산업 리포트 슬라이드 10장 생성 (1920x1080 landscape)"""
    from PIL import Image, ImageDraw

    summary_file = OUTPUTS_DIR / slug / "summary.md"
    if not summary_file.exists():
        print(f"⚠️  summary.md 없음: {summary_file}")
        return []

    content = summary_file.read_text(encoding="utf-8")

    def extract(pattern, default=""):
        m = re.search(pattern, content)
        return m.group(1).strip() if m else default

    # 기본 정보
    title_m = re.search(r'^# (.+?) 산업', content, re.MULTILINE)
    industry = title_m.group(1) if title_m else slug
    broker   = extract(r'\*\*증권사\*\*[^:]*:\s*\**([^(\n\*]+)', "증권사")
    date     = extract(r'\*\*발행일\*\*:\s*([^\n]+)', "")
    rpt_title = extract(r'\*\*리포트 제목\*\*:\s*([^\n]+)', "")

    # 섹션 파싱
    summary_points = _parse_bullets(_parse_section(content, "핵심 요약"))
    current_state  = _parse_section(content, "현황").replace('\n', ' ')
    outlook_text   = _parse_section(content, "전망").replace('\n', ' ')
    conclusion_text= _parse_section(content, "결론").replace('\n', ' ')
    invest_points  = _parse_bullets(_parse_section(content, "투자 포인트"))

    # 트렌드 파싱
    trend_pattern = re.findall(r'\*\*\d+\.\s*(.+?)\*\*\n([\s\S]+?)(?=\n\*\*\d+\.|\n---|\n## |\Z)', content)
    trends = [{"title": t.strip(), "body": b.strip().replace('\n', ' ')} for t, b in trend_pattern[:3]]
    while len(trends) < 3:
        trends.append({"title": "", "body": ""})

    # 지표 테이블
    metrics = []
    for line in content.split('\n'):
        line = line.strip()
        if not line.startswith('|') or '---' in line:
            continue
        parts = [p.strip() for p in line.strip('|').split('|')]
        if len(parts) < 3 or parts[0] in ('항목', ''):
            continue
        metrics.append((parts[0], parts[1], parts[2]))

    images_dir = OUTPUTS_DIR / slug / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    BG      = (13,  27,  42)
    WHITE   = (255, 255, 255)
    RED     = (220,  38,  38)
    GRAY    = (160, 170, 185)
    CARD_BG = (22,  42,  62)
    GREEN   = (34,  197,  94)
    BLUE    = (59,  130, 246)
    YELLOW  = (250, 204,  21)

    W, H = 1920, 1080
    image_paths = []
    slide_idx = [0]

    def save_slide(img):
        slide_idx[0] += 1
        out = images_dir / f"{slug}-img-{slide_idx[0]:02d}.png"
        img.save(str(out))
        image_paths.append(out)
        print(f"  ✅ 슬라이드 {slide_idx[0]}: {out.name}")

    def hdr(d, text):
        d.text((W // 2, 58), text, font=_load_font(36), fill=GRAY, anchor="mm")
        d.line([(80, 96), (W - 80, 96)], fill=(40, 60, 80), width=2)

    def ftr(d):
        d.line([(80, H - 90), (W - 80, H - 90)], fill=(40, 60, 80), width=2)
        info = f"리포트읽어드림  |  출처: {broker.strip()}" + (f"  |  {date}" if date else "")
        d.text((W // 2, H - 48), info, font=_load_font(30), fill=GRAY, anchor="mm")

    # ── 슬라이드 1: 타이틀 ──
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((W // 2, 110), "리포트읽어드림", font=_load_font(42), fill=GRAY, anchor="mm")
    d.line([(W // 2 - 220, 155), (W // 2 + 220, 155)], fill=(40, 60, 80), width=2)
    d.text((W // 2, H // 2 - 110), industry, font=_load_font(120, bold=True), fill=WHITE, anchor="mm")
    d.text((W // 2, H // 2 + 20), "산업 리포트 분석", font=_load_font(52), fill=GRAY, anchor="mm")
    if rpt_title:
        for i, line in enumerate(_wrap(rpt_title, 36)[:2]):
            d.text((W // 2, H // 2 + 120 + i * 62), line, font=_load_font(44), fill=GRAY, anchor="mm")
    broker_info = f"{broker.strip()}  |  {date}" if date else broker.strip()
    d.text((W // 2, H - 55), broker_info, font=_load_font(34), fill=(80, 110, 140), anchor="mm")
    save_slide(img)

    # ── 슬라이드 2: 핵심 요약 (2×2 그리드) ──
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    hdr(d, "핵심 요약")
    d.text((W // 2, 158), f"{industry} 리포트 핵심 4가지", font=_load_font(64, bold=True), fill=WHITE, anchor="mm")
    colors = [RED, GREEN, BLUE, YELLOW]
    grid = [(W // 4, H // 2 - 80), (3 * W // 4, H // 2 - 80),
            (W // 4, H // 2 + 200), (3 * W // 4, H // 2 + 200)]
    for i, (cx, cy) in enumerate(grid):
        pt = summary_points[i] if i < len(summary_points) else ""
        _rounded_rect(d, (cx - 390, cy - 100, cx + 390, cy + 100), 18, CARD_BG)
        d.text((cx - 330, cy), f"0{i+1}", font=_load_font(56, bold=True), fill=colors[i], anchor="lm")
        for j, ln in enumerate(_wrap(pt, 19)[:2]):
            d.text((cx - 220, cy - 22 + j * 46), ln, font=_load_font(36, bold=True), fill=WHITE, anchor="lm")
    ftr(d)
    save_slide(img)

    # ── 슬라이드 3: 현황 ──
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    hdr(d, "현재 산업 현황")
    d.text((W // 2, 168), f"{industry} 현황", font=_load_font(72, bold=True), fill=WHITE, anchor="mm")
    _rounded_rect(d, (80, 230, W - 80, H - 110), 22, CARD_BG)
    lines = _wrap(current_state, 38)
    for i, ln in enumerate(lines[:7]):
        d.text((W // 2, 320 + i * 72), ln, font=_load_font(44), fill=WHITE, anchor="mm")
    ftr(d)
    save_slide(img)

    # ── 슬라이드 4, 5, 6: 트렌드 ──
    num_colors = [RED, GREEN, BLUE]
    num_labels = ["①", "②", "③"]
    for ti, trend in enumerate(trends):
        img = Image.new('RGB', (W, H), BG)
        d = ImageDraw.Draw(img)
        hdr(d, f"핵심 트렌드 {ti + 1} / 3")
        left_w = 420
        d.text((left_w // 2, H // 2), num_labels[ti],
               font=_load_font(200, bold=True), fill=num_colors[ti], anchor="mm")
        d.line([(left_w, 120), (left_w, H - 110)], fill=(40, 60, 80), width=2)
        rx = left_w + 70
        ty = 180
        for ln in _wrap(trend['title'], 24)[:2]:
            d.text((rx, ty), ln, font=_load_font(72, bold=True), fill=WHITE, anchor="lm")
            ty += 86
        d.line([(rx, ty + 18), (W - 80, ty + 18)], fill=(40, 60, 80), width=2)
        by = ty + 78
        for ln in _wrap(trend['body'], 40)[:6]:
            d.text((rx, by), ln, font=_load_font(42), fill=GRAY, anchor="lm")
            by += 62
        ftr(d)
        save_slide(img)

    # ── 슬라이드 7: 주요 지표 ──
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    hdr(d, "주요 지표")
    d.text((W // 2, 160), "핵심 수치", font=_load_font(68, bold=True), fill=WHITE, anchor="mm")
    col_w = (W - 240) // 2
    row_h = 104
    sy = 230
    for i, (item, val, change) in enumerate(metrics[:8]):
        cx = 100 + (i % 2) * (col_w + 40)
        cy = sy + (i // 2) * (row_h + 16)
        _rounded_rect(d, (cx, cy, cx + col_w, cy + row_h), 12, CARD_BG)
        d.text((cx + 22, cy + row_h // 2), item, font=_load_font(36), fill=GRAY, anchor="lm")
        d.text((cx + col_w - 22, cy + row_h // 2 - 18), val,
               font=_load_font(40, bold=True), fill=WHITE, anchor="rm")
        d.text((cx + col_w - 22, cy + row_h // 2 + 22), change,
               font=_load_font(30), fill=(RED if "+" in change else GRAY), anchor="rm")
    ftr(d)
    save_slide(img)

    # ── 슬라이드 8: 전망 ──
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    hdr(d, "앞으로의 전망")
    d.text((W // 2, 168), f"{industry} 전망", font=_load_font(72, bold=True), fill=WHITE, anchor="mm")
    _rounded_rect(d, (80, 230, W - 80, H - 110), 22, CARD_BG)
    for i, ln in enumerate(_wrap(outlook_text, 38)[:7]):
        d.text((W // 2, 320 + i * 72), ln, font=_load_font(44), fill=WHITE, anchor="mm")
    ftr(d)
    save_slide(img)

    # ── 슬라이드 9: 투자 포인트 ──
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    hdr(d, "투자 포인트")
    d.text((W // 2, 165), "투자할 때 이것만 보세요", font=_load_font(62, bold=True), fill=WHITE, anchor="mm")
    ip_colors = [RED, GREEN, BLUE]
    for i, pt in enumerate(invest_points[:3]):
        cy = 265 + i * 170
        _rounded_rect(d, (80, cy, W - 80, cy + 148), 16, CARD_BG)
        d.text((180, cy + 74), "▶", font=_load_font(52, bold=True), fill=ip_colors[i], anchor="mm")
        for j, ln in enumerate(_wrap(pt, 44)[:2]):
            d.text((260, cy + 44 + j * 52), ln,
                   font=_load_font(44 if j == 0 else 40, bold=(j == 0)), fill=(WHITE if j == 0 else GRAY), anchor="lm")
    ftr(d)
    save_slide(img)

    # ── 슬라이드 10: 결론 ──
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    hdr(d, "결론")
    d.text((W // 2, 165), "오늘 리포트 핵심 정리", font=_load_font(68, bold=True), fill=WHITE, anchor="mm")
    _rounded_rect(d, (80, 230, W - 80, H - 180), 22, CARD_BG)
    for i, ln in enumerate(_wrap(conclusion_text, 40)[:6]):
        d.text((W // 2, 310 + i * 72), ln, font=_load_font(46), fill=WHITE, anchor="mm")
    _rounded_rect(d, (W // 2 - 420, H - 160, W // 2 + 420, H - 80), 40, RED)
    d.text((W // 2, H - 120), "리포트읽어드림 구독하기", font=_load_font(46, bold=True), fill=WHITE, anchor="mm")
    save_slide(img)

    return image_paths


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


def produce_industry(slug: str):
    """산업 리포트 롱폼 영상 파이프라인"""
    out_dir = OUTPUTS_DIR / slug
    if not out_dir.exists():
        available = [d.name for d in OUTPUTS_DIR.iterdir() if d.is_dir()]
        print(f"❌ 슬러그 없음: {slug}")
        print(f"   사용 가능: {available}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"🏭  리포트읽어드림 산업 리포트 롱폼")
    print(f"    슬러그: {slug}")
    print(f"{'='*50}")

    print("\n[1/3] 슬라이드 생성 중...")
    generate_industry_images(slug)

    print("\n[2/3] 음성 생성 중...")
    generate_audio(slug, "youtube")

    print("\n[3/3] 영상 조합 중...")
    generate_video(slug, "youtube")

    print(f"\n🎉 완료! → Outputs/{slug}/youtube-video.mp4")
    print("유튜브 업로드만 하면 끝이에요!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/produce.py <slug> [shorts|youtube|industry]")
        sys.exit(1)

    vtype = sys.argv[2] if len(sys.argv) > 2 else "shorts"
    if vtype == "industry":
        produce_industry(sys.argv[1])
    elif vtype == "term":
        produce_term(sys.argv[1])
    else:
        produce(slug=sys.argv[1], video_type=vtype)
