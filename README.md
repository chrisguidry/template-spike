dev-tools
=========

This is a Python environment that captures my standard development tools.  This
is a good reference for starting a new project, and it can be activated in
directories that are just Docker apps with no local virtual environment.

`Makefile` is good for _services_ that will have a committed `requirements.txt`
file in the repo.

`Makefile.library` is good for _libraries_ that specify looser requirements in
`setup.cfg`, and thus shouldn't commit a hard `requirements.txt` file to the
repo.
