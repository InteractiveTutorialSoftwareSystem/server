#!/bin/bash

# Interactive Tutorial System - Server Startup Script
# Run all servers from the server root directory for consistency

echo "🚀 Starting Interactive Tutorial System Servers"
echo "==============================================="

# Check if we're in the correct directory
if [[ ! -f "tutorial/application.py" || ! -f "auth/application.py" ]]; then
    echo "❌ Error: Please run this script from the server root directory (/Users/elouh/GenAI/ITSS/server)"
    exit 1
fi

# Function to start a server in the background
start_server() {
    local name=$1
    local port=$2
    local cmd=$3
    
    echo "🔄 Starting $name on port $port..."
    echo "   Command: $cmd"
    
    # Start the server in background
    eval "$cmd" &
    local pid=$!
    
    # Wait a moment and check if it's still running
    sleep 2
    if kill -0 $pid 2>/dev/null; then
        echo "✅ $name started successfully (PID: $pid)"
    else
        echo "❌ Failed to start $name"
        return 1
    fi
}

echo ""
echo "Starting servers from: $(pwd)"
echo ""

# Start Authentication Server (Port 5001)
start_server "Authentication Server" "5001" "PYTHONPATH=. python3 auth/application.py"

# Start Tutorial Server (Port 5002) 
start_server "Tutorial Server" "5002" "PYTHONPATH=. STORAGE_TYPE=local python3 tutorial/application.py"

echo ""
echo "🎯 Server Status:"
echo "   • Authentication Server: http://localhost:5001"
echo "   • Tutorial Server: http://localhost:5002"
echo ""
echo "📋 Next Steps:"
echo "   1. Start the frontend: cd ../client && npm start"
echo "   2. Access the application: http://localhost:3000"
echo ""
echo "⚠️  To stop all servers, run: ./stop_servers.sh"
echo ""

# Keep script running to monitor servers
echo "Press Ctrl+C to stop all servers..."
wait