#!/bin/bash

# Interactive Tutorial System - Stop All Servers Script

echo "🛑 Stopping Interactive Tutorial System Servers"
echo "==============================================="

# Kill processes by port
echo "🔄 Stopping servers on ports 5001, 5002..."

# Kill by port
lsof -ti:5001 | xargs kill -9 2>/dev/null
lsof -ti:5002 | xargs kill -9 2>/dev/null

# Kill by process name patterns
pkill -f "auth/application.py" 2>/dev/null
pkill -f "tutorial/application.py" 2>/dev/null

echo "✅ All servers stopped"
echo ""
echo "📋 To stop the frontend as well:"
echo "   • Press Ctrl+C in the frontend terminal"
echo "   • Or run: lsof -ti:3000 | xargs kill -9"
echo ""