#!/bin/bash

# Script to start the EPD Metadata Web GUI

# Frontend port (can be overridden by environment)
FRONTEND_PORT=${FRONTEND_PORT:-8082}

echo "Starting EPD Metadata Web GUI..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Start Flask backend in background
echo "Starting Flask backend on http://localhost:5001..."
python app.py &
FLASK_PID=$!

# Wait a moment for Flask to start
sleep 2

# Start frontend HTTP server
echo "Starting frontend server on http://localhost:${FRONTEND_PORT}..."
echo "Press Ctrl+C to stop both servers"
python -m http.server ${FRONTEND_PORT} &
HTTP_PID=$!

# Give the frontend a moment to come up, then open it in the default browser
sleep 1
GUI_URL="http://localhost:${FRONTEND_PORT}"
echo "Opening GUI at $GUI_URL in default browser..."
if command -v open >/dev/null 2>&1; then
    open "$GUI_URL"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$GUI_URL"
elif command -v gnome-open >/dev/null 2>&1; then
    gnome-open "$GUI_URL"
else
    echo "Could not detect a browser opener. Please open $GUI_URL manually."
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $FLASK_PID 2>/dev/null
    kill $HTTP_PID 2>/dev/null
    echo "Servers stopped."
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup INT TERM

# Wait for both processes
wait
