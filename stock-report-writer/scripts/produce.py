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
# Step 1: 이미지 생성 (Gemini API)
# ─────────────────────────────────────────

def generate_images(slug: str):
    """image-prompts.md의 프롬프트로 Gemini 이미지 생성"""
    from google import genai
    from google.genai import types
    from PIL import Image

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompts_file = OUTPUTS_DIR / slug / "images" / "image-prompts.md"
    if not prompts_file.exists():
        print(f"⚠️  image-prompts.md 없음: {prompts_file}")
        return []

    content = prompts_file.read_text(encoding="utf-8")
    prompts = re.findall(r"```\n(.*?)\n```", content, re.DOTALL)

    if not prompts:
        print("⚠️  프롬프트를 찾을 수 없음")
        return []

    image_paths = []
    for i, prompt in enumerate(prompts, 1):
        print(f"  이미지 {i}/{len(prompts)} 생성 중...")
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
                    out_path = OUTPUTS_DIR / slug / "images" / f"{slug}-img-{i:02d}.png"
                    img.save(str(out_path))
                    image_paths.append(out_path)
                    print(f"  ✅ 저장: {out_path.name}")
                    break
        except Exception as e:
            print(f"  ❌ 이미지 {i} 실패: {e}")

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

def generate_video(slug: str, video_type: str = "shorts"):
    """이미지 + 음성 → mp4 조합"""
    from moviepy.editor import (
        ImageClip, AudioFileClip, concatenate_videoclips,
        TextClip, CompositeVideoClip, ColorClip,
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
    dur_per_img = max((audio.duration - 3) / len(image_files), 1)

    print(f"  영상 길이: {audio.duration:.1f}초 / 이미지 {len(image_files)}개")

    clips = []
    for img_path in image_files:
        clip = ImageClip(str(img_path)).set_duration(dur_per_img).resize(size)
        clips.append(clip)

    # 면책 자막 (마지막 3초)
    disclaimer = (
        "본 영상은 리포트를 읽어드리는 것이며\n"
        "매수, 매도 추천이 아니며\n"
        "투자에 대한 책임은 본인에게 있습니다"
    )
    bg = ColorClip(size=size, color=(13, 27, 42)).set_duration(3)
    try:
        txt = (
            TextClip(disclaimer, fontsize=48, color="white",
                     size=(size[0] - 100, None), method="caption", align="center")
            .set_duration(3).set_position("center")
        )
        clips.append(CompositeVideoClip([bg, txt]))
    except Exception:
        clips.append(bg)   # 폰트 없으면 배경만

    video = concatenate_videoclips(clips, method="compose")
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
