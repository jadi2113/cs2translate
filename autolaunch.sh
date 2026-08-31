#!/bin/bash
DIR="$(dirname "$0")"
"$DIR/cs2translate" & exec "$@"
