#!/bin/bash

for i in {1..500}
do
  curl -X POST http://localhost:8000/signals \
  -H "Content-Type: application/json" \
  -d '{"component_id":"DB","message":"failure","timestamp":"2026-01-01T10:00:00"}' &
done

wait
echo "Done"
