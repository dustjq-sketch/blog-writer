"""
dashboard/backend/api_conversations.py
Remote Claude Bot 대화 기록 조회 API
"""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

BASE_DIR = Path(__file__).parent.parent.parent
CONVERSATIONS_DIR = BASE_DIR / 'data' / 'conversations'

router = APIRouter()


def _load_day(date_str: str) -> list:
    p = CONVERSATIONS_DIR / f"{date_str}.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return []


@router.get("/conversations/dates")
async def list_dates():
    """대화 기록이 있는 날짜 목록을 최신순으로 반환한다."""
    if not CONVERSATIONS_DIR.exists():
        return []
    dates = sorted(
        (p.stem for p in CONVERSATIONS_DIR.glob("*.json")),
        reverse=True,
    )
    return dates


@router.get("/conversations/{date}")
async def get_conversations(date: str):
    """특정 날짜(YYYY-MM-DD)의 대화 목록을 반환한다."""
    # 날짜 형식 기본 검증
    if len(date) != 10 or date[4] != '-' or date[7] != '-':
        raise HTTPException(status_code=400, detail="날짜 형식은 YYYY-MM-DD 이어야 합니다.")
    items = _load_day(date)
    if not items and not (CONVERSATIONS_DIR / f"{date}.json").exists():
        raise HTTPException(status_code=404, detail="해당 날짜의 대화 기록이 없습니다.")
    return items
