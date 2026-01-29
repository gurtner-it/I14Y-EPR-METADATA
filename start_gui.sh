#!/bin/bash

# Script to start the EPD Metadata Web GUI

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
echo "Starting frontend server on http://localhost:8080..."
echo "Press Ctrl+C to stop both servers"
python -m http.server 8082 &
HTTP_PID=$!

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
