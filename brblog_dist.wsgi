import sys
sys.path.insert(0, '/path/to/the/app')

activate_this = '/path/to/the/app/venv/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

from brblog import app as application

# vim: set ft=python:
