import io

from .. import get_logger
from .base import *
from ..cldr import CP_REGEX

logger = get_logger(__file__)

keysym_to_str = {}

with open(filepath(__file__, 'bin', 'keysym.tsv')) as f:
    line = f.readline()
    while line:
        if line.startswith("*"):
            break
        line = f.readline()

    line = f.readline()
    while line:
        string, keysymstr = line.strip().split('\t')
        keysym = int(keysymstr, 16)

        keysym_to_str[keysym] = string
        line = f.readline()

class XKBGenerator(Generator):
    def generate(self, base='.'):
        if not self.sanity_check():
            return
        
        self.build_dir = os.path.abspath(base)
        os.makedirs(self.build_dir, exist_ok=True)

        if self.dry_run:
            logger.info("Dry run completed.")
            return

        xkb_fn = os.path.join(self.build_dir, "%s.xkb" % (
            self._project.internal_name))
        xcompose_fn = os.path.join(self.build_dir, "%s.xcompose" % (
            self._project.internal_name))

        # First char in Supplemental Private Use Area-A
        self.surrogate = 0xF0000
        self.xkb = open(xkb_fn, 'w')
        self.xcompose = open(xcompose_fn, 'w')

        for name, layout in self.supported_layouts.items():
            self.write_nonsense(name, layout)

        self.xkb.close()
        self.xcompose.close()

    def filter_xkb_keysyms(self, v):
        """actual filter function"""
        if v is None:
            return ''

        v = CP_REGEX.sub(lambda x: chr(int(x.group(1), 16)), v)

        if len(v) > 1:
            cps = " ".join(["U%04X" % ord(x) for x in v])
            self.xcompose.write("<U%X> : %s # %s\n" % (self.surrogate, cps, v))
            o = self.surrogate
            self.surrogate += 1
        else:
            o = ord(v)
        return keysym_to_str.get(o, "U%04X" % o)

    def write_nonsense(self, name, layout):
        buf = self.xkb
        ligs = self.xcompose

        ligs.write("# %s\n" % name)

        buf.write("default partial alphanumeric_keys\n")
        buf.write('xkb_symbols "basic" {\n\n')
        buf.write('    include "latin"\n')
        buf.write('    name[Group1] = "%s";\n\n' % layout.display_names[layout.locale])

        col0 = mode_iter(layout, 'iso-default', required=True)
        col1 = mode_iter(layout, 'iso-shift')
        col2 = mode_iter(layout, 'iso-alt')
        col3 = mode_iter(layout, 'iso-alt+shift')

        def xkb_filter(self, *args):
            out = [self.filter_xkb_keysyms(i) for i in args]
            while len(out) > 0 and out[-1] == '':
                out.pop()
            return tuple(out)

        for (iso, c0, c1, c2, c3) in zip(ISO_KEYS, col0, col1, col2, col3):
            cols = ", ".join("%10s" % x for x in xkb_filter(self, c0, c1, c2, c3))
            buf.write("    key <A%s> { [ %s ] };\n" % (iso, cols))

        buf.write('\n    include "level3(ralt_switch)"\n};\n\n')
        ligs.write('\n')
