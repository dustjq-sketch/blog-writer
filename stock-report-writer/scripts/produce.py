"""
리포트읽어드림 - 영상 자동 제작 스크립트
Usage:
    python produce.py <slug> [shorts|youtube]
    python produce.py semco-20260403 shorts
    python produce.py daedeok-20260401 youtube
"""

import os
import sys
import re
import io
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
OUTPUTS_DIR = BASE_DIR / "Outputs"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# ─────────────────────────────────────────
# Step 1: 이미지 생성 (Gemini API)
# ─────────────────────────────────────────

def generate_images(slug: str):
    """image-prompts.md의 프롬프트로 Gemini 이미지 생성"""
    import google.generativeai as genai
    from PIL import Image

    genai.configure(api_key=GEMINI_API_KEY)

    prompts_file = OUTPUTS_DIR / slug / "images" / "image-prompts.md"
    if not prompts_file.exists():
        print(f"⚠️  image-prompts.md 없음: {prompts_file}")
        return []

    content = prompts_file.read_text(encoding="utf-8")
    prompts = re.findall(r"```\n(.*?)\n```", content, re.DOTALL)

    if not prompts:
        print("⚠️  프롬프트를 찾을 수 없음")
        return []

    model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")
    image_paths = []

    for i, prompt in enumerate(prompts, 1):
        print(f"  이미지 {i}/{len(prompts)} 생성 중...")
        try:
            response = model.generate_content(
                prompt.strip(),
                generation_config={"response_modalities": ["IMAGE", "TEXT"]},
            )
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    img = Image.open(io.BytesIO(part.inline_data.data))
                    out_path = OUTPUTS_DIR / slug / "images" / f"{slug}-img-{i:02d}.png"
                    img.save(str(out_path))
                    image_paths.append(out_path)
                    print(f"  ✅ 저장: {out_path.name}")
                    break
        except Exception as e:
            print(f"  ❌ 이미지 {i} 생성 실패: {e}")

    return image_paths


# ─────────────────────────────────────────
# Step 2: 썸네일 생성 (Gemini API)
# ─────────────────────────────────────────

def generate_thumbnails(slug: str, video_type: str = "shorts"):
    """thumbnail-prompts.md로 썸네일 생성"""
    import google.generativeai as genai
    from PIL import Image

    genai.configure(api_key=GEMINI_API_KEY)

    prompts_file = OUTPUTS_DIR / slug / "thumbnail-prompts.md"
    if not prompts_file.exists():
        print(f"⚠️  thumbnail-prompts.md 없음")
        return

    content = prompts_file.read_text(encoding="utf-8")
    prompts = re.findall(r"```\n(.*?)\n```", content, re.DOTALL)

    model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")

    names = ["thumbnail-shorts.png", "thumbnail-youtube.png"]
    for i, (prompt, name) in enumerate(zip(prompts, names)):
        if video_type == "shorts" and i == 1:
            continue
        if video_type == "youtube" and i == 0:
            continue

        print(f"  썸네일 생성 중: {name}")
        try:
            response = model.generate_content(
                prompt.strip(),
                generation_config={"response_modalities": ["IMAGE", "TEXT"]},
            )
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    img = Image.open(io.BytesIO(part.inline_data.data))
                    out_path = OUTPUTS_DIR / slug / name
                    img.save(str(out_path))
                    print(f"  ✅ 저장: {out_path.name}")
                    break
        except Exception as e:
            print(f"  ❌ 썸네일 생성 실패: {e}")


# ─────────────────────────────────────────
# Step 3: 음성 생성 (Google Cloud TTS)
# ─────────────────────────────────────────

def extract_narration(script_md: str) -> str:
    """스크립트에서 나레이션 텍스트만 추출 (대괄호 지문 제거)"""
    lines = script_md.split("\n")
    narration = []

    # 스크립트 섹션만 추출
    in_script = False
    for line in lines:
        if "## 스크립트" in line:
            in_script = True
            continue
        if in_script and line.startswith("## "):
            break
        if not in_script:
            continue

        # 대괄호 지문 제거: [화면 전환], [자막: ...] 등
        line = re.sub(r"\[.*?\]", "", line)
        # 마크다운 기호 제거
        line = line.strip().strip('"').strip("*").strip("#").strip("━")
        # 표 행 제거
        if "|" in line:
            continue
        if line:
            narration.append(line)

    text = " ".join(narration)
    # 면책 문구 추가
    text += " 본 영상은 리포트를 읽어드리는 것이며 매수, 매도 추천이 아니며 투자에 대한 책임은 본인에게 있습니다."
    return text


def generate_audio(slug: str, video_type: str = "shorts"):
    """Google Cloud TTS로 한국어 음성 생성"""
    from google.cloud import texttospeech

    script_file = OUTPUTS_DIR / slug / f"{video_type}-script.md"
    if not script_file.exists():
        print(f"⚠️  스크립트 없음: {script_file}")
        return None

    script_text = script_file.read_text(encoding="utf-8")
    narration = extract_narration(script_text)

    print(f"  나레이션 길이: {len(narration)}자")

    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=narration)
    voice = texttospeech.VoiceSelectionParams(
        language_code="ko-KR",
        name="ko-KR-Neural2-C",   # 자연스러운 한국어 남성 목소리
        # 여성 목소리: ko-KR-Neural2-A 또는 ko-KR-Neural2-B
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.1,   # 약간 빠르게 (쇼츠용)
        pitch=0.0,
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
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
        TextClip, CompositeVideoClip, ColorClip
    )
    from PIL import Image as PILImage
    import numpy as np

    audio_path = OUTPUTS_DIR / slug / f"audio-{video_type}.mp3"
    images_dir = OUTPUTS_DIR / slug / "images"
    output_path = OUTPUTS_DIR / slug / f"{video_type}-video.mp4"

    if not audio_path.exists():
        print("⚠️  음성 파일 없음. generate_audio 먼저 실행하세요.")
        return

    # 해상도 설정
    if video_type == "shorts":
        size = (1080, 1920)
    else:
        size = (1920, 1080)

    # 이미지 파일 로드 (생성된 이미지 우선, 없으면 썸네일)
    image_files = sorted(images_dir.glob(f"{slug}-img-*.png"))
    if not image_files:
        print("⚠️  생성된 이미지 없음. 썸네일로 대체합니다.")
        thumb = OUTPUTS_DIR / slug / f"thumbnail-{video_type}.png"
        if thumb.exists():
            image_files = [thumb]
        else:
            print("❌ 사용할 이미지 없음")
            return

    # 오디오 로드
    audio = AudioFileClip(str(audio_path))
    total_duration = audio.duration

    # 각 이미지 표시 시간 (마지막 3초는 면책 자막)
    content_duration = max(total_duration - 3, 1)
    dur_per_img = content_duration / len(image_files)

    print(f"  영상 길이: {total_duration:.1f}초 / 이미지 {len(image_files)}개 / 장당 {dur_per_img:.1f}초")

    clips = []
    for img_path in image_files:
        clip = (
            ImageClip(str(img_path))
            .set_duration(dur_per_img)
            .resize(size)
        )
        clips.append(clip)

    # 면책 자막 슬라이드 (마지막 3초)
    disclaimer = "본 영상은 리포트를 읽어드리는 것이며\n매수, 매도 추천이 아니며\n투자에 대한 책임은 본인에게 있습니다"
    bg = ColorClip(size=size, color=(13, 27, 42)).set_duration(3)   # 다크 네이비
    txt = (
        TextClip(disclaimer, fontsize=48, color="white", font="NanumGothic",
                 size=(size[0] - 100, None), method="caption", align="center")
        .set_duration(3)
        .set_position("center")
    )
    disclaimer_clip = CompositeVideoClip([bg, txt])
    clips.append(disclaimer_clip)

    # 조합 & 오디오 합치기
    video = concatenate_videoclips(clips, method="compose")
    video = video.set_audio(audio.set_duration(video.duration))

    video.write_videofile(
        str(output_path),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger=None,
    )
    print(f"  ✅ 영상 저장: {output_path}")


# ─────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────

def produce(slug: str, video_type: str = "shorts"):
    out_dir = OUTPUTS_DIR / slug
    if not out_dir.exists():
        print(f"❌ 슬러그 폴더 없음: {slug}")
        print(f"   사용 가능한 슬러그: {[d.name for d in OUTPUTS_DIR.iterdir() if d.is_dir()]}")
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
        print("Usage: python produce.py <slug> [shorts|youtube]")
        print("Example: python produce.py semco-20260403 shorts")
        sys.exit(1)

    slug_arg = sys.argv[1]
    type_arg = sys.argv[2] if len(sys.argv) > 2 else "shorts"
    produce(slug_arg, type_arg)
