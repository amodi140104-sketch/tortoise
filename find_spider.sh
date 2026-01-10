#!/bin/bash

# Navigate to Scrapy project
cd "/mnt/c/Users/Animesh Modi/Desktop/Apache_Kafka/FDP/tortoise"

echo "==========================================
echo "SCRAPY PROJECT DIAGNOSTICS"
echo "=========================================="
echo ""

echo "1. Current directory:"
pwd
echo ""

echo "2. Available spiders:"
scrapy list
echo ""

echo "3. Spider files in project:"
find . -name "*spider*.py" -type f
echo ""

echo "4. Contents of tortoise/spiders directory:"
ls -la tortoise/spiders/ 2>/dev/null || echo "Directory not found"
echo ""

echo "5. Checking spider class names in files:"
grep -r "class.*Spider" tortoise/spiders/*.py 2>/dev/null || echo "No spider classes found"
echo ""

echo "=========================================="