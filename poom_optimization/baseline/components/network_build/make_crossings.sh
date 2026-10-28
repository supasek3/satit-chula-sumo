#!/bin/bash
# Builds network_crossings.net.xml with the two signalized crossings.
# network.net.xml is never modified.
cd "$(dirname "$0")"
NETCONVERT=netconvert
command -v netconvert >/dev/null || NETCONVERT="$SUMO_HOME/bin/netconvert"
python3 fix_sidewalks.py || exit 1
"$NETCONVERT" -s network_base.net.xml \
  --node-files crossings.nod.xml \
  --edge-files crossings.edg.xml \
  --connection-files crossings.con.xml \
  --walkingareas \
  --no-internal-links false \
  --tls.set 10072794956,J1 \
  --tls.rebuild \
  -o network_crossings.net.xml \
&& echo "OK -> network_crossings.net.xml" \
&& echo "crossings built: $(grep -c 'function="crossing"' network_crossings.net.xml) (expect 2)" \
&& grep -A6 '<tlLogic' network_crossings.net.xml
