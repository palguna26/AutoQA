#!/bin/bash
# Development script to run AutoQA with ngrok

set -e

echo "Starting AutoQA development server..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Please create .env file with required environment variables"
    exit 1
fi

# Start uvicorn in background
echo "Starting uvicorn server on port 8000..."
uvicorn src.app.main:app --reload --port 8000 &
UVICORN_PID=$!

# Wait for server to start
sleep 3

# Start ngrok
echo "Starting ngrok..."
ngrok http 8000 &
NGROK_PID=$!

# Wait for ngrok to start
sleep 3

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*\.ngrok[^"]*' | head -1)

if [ -z "$NGROK_URL" ]; then
    echo "Error: Could not get ngrok URL"
    kill $UVICORN_PID $NGROK_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo "========================================="
echo "AutoQA is running!"
echo "Local URL: http://localhost:8000"
echo "Public URL: $NGROK_URL"
echo "Webhook URL: $NGROK_URL/webhooks/github"
echo ""
echo "Press Ctrl+C to stop"
echo "========================================="
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $UVICORN_PID $NGROK_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for processes
wait

