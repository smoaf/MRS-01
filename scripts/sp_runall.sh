#!/bin/bash
cd /home/claude
for tag in b350 b256; do for name in plate shell; do for conn in pins keys lap; do
  timeout 1200 bvenv/bin/python scripts/sp_build.py -- $name $tag $conn > v8/split/build/log_${name}_${tag}_${conn}.txt 2>&1
  echo "$name $tag $conn: $(grep -E '^total|^assembly|NOT FIT|Traceback' v8/split/build/log_${name}_${tag}_${conn}.txt | cut -c1-230 | tr '\n' ' ')"
done; done; done
echo ALLDONE
