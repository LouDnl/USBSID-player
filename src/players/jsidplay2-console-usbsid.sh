#!/bin/bash
PLAYERS=$(find * -type d -iname players)
export LD_LIBRARY_PATH=.:./$PLAYERS
java -classpath "jsidplay2-4.12-ui.jar:${PLAYERS}/*" sidplay.ConsolePlayer "$@"
