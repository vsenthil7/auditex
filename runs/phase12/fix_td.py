import sys
p = sys.argv[1]
d = open(p, 'rb').read()
old = b'fireEvent, act'
new = b'act'
if old in d:
    open(p, 'wb').write(d.replace(old, new, 1))
    print('patched')
else:
    print('already patched')
