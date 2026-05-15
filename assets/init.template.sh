#!/bin/bash
# init.sh - Environment initialization script

set -e  # Exit on error

echo "🔧 Initializing assignment environment..."

# Navigate to project directory
cd "$(dirname "$0")"

# TODO: Add your setup commands here
# Examples:
# - npm install
# - pip install -r requirements.txt
# - docker-compose up -d
# - source .env

# TODO: Start services if needed
# Examples:
# - npm run dev &
# - python manage.py runserver &

# TODO: Run health checks
# Examples:
# - curl -f http://localhost:3000
# - npm run test:quick

echo "✅ Initialization complete"
echo "📋 Read 00-current/progress.log for latest status"
echo "📝 Read 00-current/item-list.json for pending items"
echo "📁 Per-item workspaces: 20-working/<ITEM-ID>/"
