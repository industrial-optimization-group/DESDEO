#!/bin/bash

# ANSI color codes
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Function to prepend colored (Backend) to each line of output
prepend_backend() {
    while IFS= read -r line; do
        echo -e "${BLUE}(Backend)${NC} $line"
    done
}

# Function to prepend colored (Frontend) to each line of output
prepend_frontend() {
    while IFS= read -r line; do
        echo -e "${YELLOW}(Frontend)${NC} $line"
    done
}

# Function to kill background processes
cleanup() {
    echo "Shutting down..."
    kill -TERM $backend_pid $frontend_pid
    wait $backend_pid $frontend_pid
    exit 0
}

# Trap SIGINT (Ctrl+C) and call cleanup function
trap cleanup SIGINT

# Run Uvicorn from the ./desdeo/api directory and prepend colored (Backend) to its output
(cd ./desdeo/api && uvicorn app:app --reload --log-level debug --host 127.0.0.1 --port 8000) | prepend_backend &
backend_pid=$!

# Run npm command from the ./webgui directory and prepend colored (Frontend) to its output
(cd ./webui && npm run dev -- --open) | prepend_frontend &
frontend_pid=$!

wait $backend_pid $frontend_pid
