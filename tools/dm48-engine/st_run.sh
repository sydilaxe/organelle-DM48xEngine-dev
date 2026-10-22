#!/bin/bash
# usage: st_run.sh bow note -> env~ dB every ~0.56 s for 6 s (isolated Steel engine)
D="/tmp/claude-0/-home-user/45dfc138-ac93-5e31-80db-a509a4f89018/scratchpad/DM48 Engine"
sed "s/s4 1/s4 $1/; s/msg 20 120 57 0/msg 20 120 ${2:-57} 0/" "$(dirname "$0")/st_test.pd" > "$D/st2.pd"
cd "$D" && timeout 30 pd -nosound -nomidi -batch -stderr -open st2.pd 2>&1 | grep ENV | awk 'NR%6==2{printf "%.0f ", $2}'; rm -f st2.pd
