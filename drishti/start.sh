#!/bin/bash
set -e

echo "════════════════════════════════════"
echo "  DRISHTI — Starting Platform"
echo "  IDBI Innovate 2026"
echo "════════════════════════════════════"

# Backend setup
cd "$(dirname "$0")/backend"
pip install -r requirements.txt -q
echo "✓ Dependencies installed"

python -c "from database.seed import seed_all; seed_all()"
echo "✓ Demo data seeded"

uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "✓ Backend running on http://localhost:8000"

# Wait for backend
sleep 3

# Frontend setup
cd ../frontend
npm install -q
echo "✓ Frontend dependencies installed"

npm run dev &
FRONTEND_PID=$!
echo "✓ Frontend running on http://localhost:5173"

echo ""
echo "════════════════════════════════════"
echo "  DRISHTI is live!"
echo "  Open: http://localhost:5173"
echo "  API:  http://localhost:8000/docs"
echo "════════════════════════════════════"

wait $BACKEND_PID $FRONTEND_PID
