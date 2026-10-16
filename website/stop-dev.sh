#!/bin/bash

# SentinelGrid Website - Development Server Stop Script

echo "🛑 Stopping SentinelGrid Website Development Server..."
echo ""

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$SCRIPT_DIR/.dev-server.pid"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  No running development server found"
    echo "   (PID file not found: $PID_FILE)"
    exit 1
fi

# Read the PID
PID=$(cat "$PID_FILE")

# Check if the process is running
if ps -p $PID > /dev/null 2>&1; then
    echo "📍 Found development server (PID: $PID)"
    
    # Kill the process
    kill $PID
    
    # Wait for the process to terminate
    echo "⏳ Waiting for server to stop..."
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    # Check if process is still running
    if ps -p $PID > /dev/null 2>&1; then
        echo "⚠️  Process didn't stop gracefully, forcing..."
        kill -9 $PID
        sleep 1
    fi
    
    # Remove PID file
    rm "$PID_FILE"
    
    echo "✅ Development server stopped successfully!"
else
    echo "⚠️  Process with PID $PID is not running"
    echo "   Cleaning up PID file..."
    rm "$PID_FILE"
    echo "✅ Cleanup complete"
fi

echo ""

