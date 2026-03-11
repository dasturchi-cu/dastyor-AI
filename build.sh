#!/usr/bin/env bash
# Render Build Script - Dastyor AI

echo "Installing Python requirements..."
pip install -r requirements.txt

echo "Installing Playwright Chromium browser..."
playwright install chromium