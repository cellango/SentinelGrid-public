#!/bin/bash

# SentinelGrid Website - Development Server Start Script

echo "🚀 Starting SentinelGrid Website Development Server (HTTPS)..."
echo ""

DEV_HTTPS_PORT=${DEV_HTTPS_PORT:-3444}
export PORT="$DEV_HTTPS_PORT"
export NEXT_PUBLIC_FORCE_HTTPS=${NEXT_PUBLIC_FORCE_HTTPS:-true}
export NEXT_PUBLIC_HTTPS_PORT="$DEV_HTTPS_PORT"

# Move to script directory so npm commands run in website/
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$SCRIPT_DIR/.dev-server.pid"
cd "$SCRIPT_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Check if server is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "⚠️  Development server is already running (PID: $PID)"
        echo "   Visit: https://localhost:${DEV_HTTPS_PORT}"
        echo ""
        echo "   To stop the server, run: ./stop-dev.sh"
        exit 1
    else
        # PID file exists but process is not running, clean it up
        rm "$PID_FILE"
    fi
fi

# Start the development server in the background
echo "🎨 Starting Next.js development server on https://localhost:${DEV_HTTPS_PORT} ..."
nohup npm run dev:https > "$SCRIPT_DIR/.dev-server.log" 2>&1 &
SERVER_PID=$!

# Save the PID
echo $SERVER_PID > "$PID_FILE"

# Wait a moment for the server to start
sleep 3

# Check if the process is still running
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "✅ Development server started successfully!"
    echo ""
    echo "   🌐 Website URL: https://localhost:${DEV_HTTPS_PORT}"
    echo "   📝 Logs: tail -f $SCRIPT_DIR/.dev-server.log"
    echo "   🛑 Stop: ./stop-dev.sh"
    echo ""
    echo "💡 The redesigned website is now running with:"
    echo "   • New modern logo"
    echo "   • Interactive pricing calculator"
    echo "   • ICP-focused sections"
    echo "   • 17 rotating security statements"
    echo "   • Ultra-modern visual design"
    echo ""
else
    echo "❌ Failed to start development server"
    echo "   Check logs: cat $SCRIPT_DIR/.dev-server.log"
    rm "$PID_FILE"
    exit 1
fi
