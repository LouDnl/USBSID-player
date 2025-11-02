#!/bin/bash
export LD_LIBRARY_PATH=.:./players
java -classpath "jsidplay2-4.12-ui.jar:players/*" sidplay.ConsolePlayer "$@"
