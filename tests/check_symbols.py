#!/usr/bin/env python
import sysconfig
import subprocess
import os
import sys
import platform

if os.path.dirname(__file__):
    os.chdir(os.path.dirname(__file__))

if platform.system() in ('Windows', 'Darwin') or platform.system().startswith('CYGWIN'):
    sys.exit(0) # test not supported on windows or osx - ignore it

so_files = [
    sysconfig.get_config_var("LIBDIR")+"/"+sysconfig.get_config_var("LDLIBRARY"),
    sysconfig.get_config_var("LIBPL")+"/"+sysconfig.get_config_var("LDLIBRARY"),
]
so_file = None
for name in so_files:
    if os.path.isfile(name):
        so_file = name
if not so_file:
    print('Could not find %r' % so_files)
    sys.exit(1)

so_symbols = set()
for line in subprocess.check_output(['readelf', '-Ws', so_file]).splitlines():
    if line:
        so_symbols.add(line.decode('utf-8').split()[-1])

assert 'PyList_Type' in so_symbols
assert 'PyList_New' in so_symbols

cargo_cmd = ['cargo', 'rustc']
cfgs = []
if sys.version_info.major == 3:
    cargo_cmd += ['--manifest-path', '../python3-sys/Cargo.toml']
    for i in range(4, sys.version_info.minor+1):
        cfgs += ['--cfg', 'Py_3_{}'.format(i)]
else:
    cargo_cmd += ['--manifest-path', '../python27-sys/Cargo.toml']

interesting_config_flags = [
    "Py_USING_UNICODE",
    "Py_UNICODE_WIDE",
    "WITH_THREAD",
    "Py_DEBUG",
    "Py_REF_DEBUG",
    "Py_TRACE_REFS",
    "COUNT_ALLOCS"
]
for name in interesting_config_flags:
    if sysconfig.get_config_var(name):
        cfgs += ['--cfg', 'py_sys_config="{}"'.format(name)]
interesting_config_values = ['Py_UNICODE_SIZE']
for name in interesting_config_values:
    cfgs += ['--cfg', 'py_sys_config="{}_{}"'.format(name, sysconfig.get_config_var(name))]

subprocess.call(cargo_cmd + ['--'] + cfgs)
output = subprocess.check_output(['nm', '-C', '-g', '../target/debug/libpython{}_sys.rlib'.format(3 if sys.version_info.major == 3 else 27)])
lines = output.decode('ascii').split('\n')
foreign_symbols = set()

for line in lines:
    parts = line.split(' ')
    if len(parts) > 1:
        foreign_symbols.add(parts[-1])

print(lines[:25])
print(len(foreign_symbols))
assert 'PyList_Type' in foreign_symbols, "Failed getting statics from nm"
assert 'PyList_New' in foreign_symbols, "Failed getting functions from nm"

names = sorted(foreign_symbols - so_symbols)
if names:
    print('Symbols missing in {}:'.format(so_file))
    print('\n'.join(names))
    sys.exit(1)
else:
    print('Symbols in {} OK.'.format(so_file))
