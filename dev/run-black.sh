#!/bin/bash
black . --target-version py37 --exclude "fluid|research|web|venv|.jupyter|common/messages" $1
