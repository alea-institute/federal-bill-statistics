#!/usr/bin/env bash

# check that GOVINFO_API_KEY is set
if [ -z "$GOVINFO_API_KEY" ]; then
    echo "GOVINFO_API_KEY is not set. Please set it in your environment before running."
    exit 1
fi

# keep poetry up to date
poetry update

# start by emptying the dist/ folder
rm -rf dist/*

# update tailwind
tailwind -i ./templates/tailwind.css -o ./static/tailwind.css

# copy the static/ folder into dist/
cp -r static/ dist/

# copy favicons
cp static/favicon.ico dist/
cp static/favicon.png dist/

# start a python http server on localhost:9000 to serve the static files for rendering
# make sure to trap the PID so we can kill it after
# log output access log to /tmp/http.log
python -m http.server 9000 --directory dist/ > /tmp/http.log 2>&1 &
HTTP_PID=$!

# parse today's bills
PYTHONPATH=. poetry run python fbs/commands/parse_bills.py

# update statistics
PYTHONPATH=. poetry run python fbs/commands/calculate_stats.py

# render all bills
PYTHONPATH=. poetry run python fbs/commands/render_all_bills.py

# build the index and related pages
PYTHONPATH=. poetry run python fbs/commands/build_site.py

# kill the python http server
kill $HTTP_PID