#!/bin/bash
# usage: tload.sh dir  -> loads main.pd for 0.5 s, prints errors / exit code
cat > "$1/t_load.pd" <<'PD'
#N canvas 0 0 400 300 10;
#X obj 20 20 loadbang;
#X obj 20 45 delay 500;
#X msg 20 70 \; pd quit;
#X obj 200 20 main;
#X obj 20 120 catch~ outL;
#X obj 120 120 catch~ outR;
#X connect 0 0 1 0;
#X connect 1 0 2 0;
PD
cd "$1" && timeout 15 pd -nosound -nomidi -batch -stderr -open t_load.pd 2>&1 | grep -v "^verbose" | head -${2:-15}; echo "exit ${PIPESTATUS[0]}"
