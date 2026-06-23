#!/usr/bin/env bash

set -e

CURRENT_BRANCH=$(git branch --show-current)

if [ -z "$CURRENT_BRANCH" ]; then
    echo "❌ No branch checked out (detached HEAD)."
    exit 1
fi

echo "Current branch: $CURRENT_BRANCH"
echo "Fetching from origin..."

git fetch origin

echo "Resetting to origin/$CURRENT_BRANCH..."

git reset --hard "origin/$CURRENT_BRANCH"

echo "✅ Branch '$CURRENT_BRANCH' synchronized with 'origin/$CURRENT_BRANCH'"