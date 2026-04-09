#!/bin/bash
# 리포트읽어드림 - 서버 시작 스크립트
# 이 파일을 더블클릭하면 서버가 시작되고 대시보드가 열려요

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "======================================"
echo "  📊 리포트읽어드림 서버 시작"
echo "======================================"

# 기존 서버 종료
lsof -ti:5001 | xargs kill -9 2>/dev/null && echo "기존 서버 종료됨" || true

# Flask 설치 확인
if ! python3 -c "import flask" 2>/dev/null; then
  echo "Flask 설치 중..."
  pip3 install flask -q
fi

echo ""
echo "서버 시작 중..."
python3 server/app.py &
SERVER_PID=$!

# 브라우저 열기
sleep 2
open http://localhost:5001
echo "✅ 브라우저가 열렸어요: http://localhost:5001"
echo ""
echo "이 창을 닫으면 서버가 종료돼요."
echo "종료하려면 Ctrl+C 를 누르세요."
echo "======================================"

wait $SERVER_PID
