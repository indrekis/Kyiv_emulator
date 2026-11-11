#!/usr/bin/env python3
"""Shared, fail-closed launcher for MSYS2 MINGW64 from native Python.

The Python->MSYS2 Bash transition may discard MSYSTEM/MINGW_PREFIX and
prioritize /usr/bin over /mingw64/bin. This module selects the Bash executable
from the same MSYS2 installation as Python, then restores the environment
*inside* that Bash process. Do not substitute a plain subprocess(['bash',...]).

All command strings are trusted developer-authored inputs. Never interpolate
untrusted shell arguments into qt_mingw_bootstrap's body.
"""
from __future__ import annotations
from pathlib import Path
import sys

def msys2_bash_from_python(python_executable=None):
    """Select Bash from this MINGW64 Python's own MSYS2 installation.

    Windows-native Python may scrub MSYSTEM/MINGW_PREFIX when launching an
    MSYS bash. Selecting bash.exe explicitly is necessary but not sufficient:
    the command also bootstraps the MINGW64 environment *inside* Bash.
    """
    exe=Path(python_executable or sys.executable).resolve()
    if exe.parent.name.lower()!='bin' or exe.parent.parent.name.lower()!='mingw64':
        raise RuntimeError('QT_MSYS2_PYTHON_NOT_MINGW64:'+str(exe))
    bash=exe.parents[2]/'usr'/'bin'/'bash.exe'
    if bash.is_symlink() or not bash.is_file():
        raise RuntimeError('QT_MSYS2_BASH_NOT_IN_PYTHON_INSTALL:'+str(bash))
    return str(bash)


def qt_mingw_bootstrap(prefix='/mingw64',run_gui=True):
    """Run Qt smoke with a strict explicit environment, not inherited shell startup.

    Only /mingw64 is used in production. Prefix override is for isolated
    non-Windows integration tests that reproduce a scrubbed Bash environment.
    Source run.sh *in the initialized Bash* so there is no second shell startup
    that might discard MSYSTEM or select /usr/bin/pkg-config again.
    """
    import re
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+',prefix) or '..' in prefix.split('/'):
        raise RuntimeError('QT_MINGW_PREFIX_INVALID')
    if type(run_gui) is not bool:raise RuntimeError('QT_RUN_GUI_FLAG_INVALID')
    instructions=(
        'set -euo pipefail',
        'export MSYSTEM=MINGW64',
        'export MINGW_PREFIX='+prefix,
        'export PATH='+prefix+'/bin:/usr/bin:/bin',
        'test "$(command -v pkg-config)" = "'+prefix+'/bin/pkg-config"',
        'test "$(command -v g++)" = "'+prefix+'/bin/g++"',
        'pkg-config --exists Qt6Widgets',
        'printf "H118_MINGW64_ENV_PASS|MSYSTEM=%s|MINGW_PREFIX=%s|QT=" "$MSYSTEM" "$MINGW_PREFIX"',
        'pkg-config --modversion Qt6Widgets',
    )
    if run_gui:instructions+=('source gui/qt6/run.sh --smoke-only',)
    return '\n'.join(instructions)+'\n'


def qt_native_argv():
    return [msys2_bash_from_python(), '--noprofile', '--norc', '-c', qt_mingw_bootstrap()]
