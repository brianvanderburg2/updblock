""" A text block updater. 

This application scans a directory recursively for a set of files and
applies a set of changes to the file to update a block of text.  The block
is delimeted by a start and end line, then the content of the block.  A
configuration file is used to define file types, block patterns, texts,
and actions.  An action combines on ore more file types with a block
pattern and text to apply to the block.

[filetype:<name>]
extensions=

line-minlength

firstline-start
firstline-end
firstline-prepad
firstline-postpad
firstline-filler
firstline-center

midline-start
midline-end
midline-center

lastline-start
lastline-end
lastline-prepad
lastline-postpad
lastline-filler
lastline-center

[text-blocks]
name=content
  can be indented

[text-files]
name=<file>

[block:<name>]
start-pattern (If omitted becomes start-pattern trimmed, with inner spaces replaced with re to match spaces)
end-pattern
start
end

[action:<name>]
filetype=...
filetype=...
text=...
block=...


"""

from __future__ import print_function

import re
try:
    import configparser
except ImportError:
    import ConfigParser as configparser


class IniAttribute(object):
    """ Information about an attribute in a configuration section. """

    def __init__(self):
        pass

    def set(self, value):
        raise NotImplementedError

    def get(self):
        return self._value


class IniListAttribute(IniAttribute):
    """ A list attribute that appends items. """

    def __init__(self, sep=","):
        IniAttribute.__init__(self)
        self._sep = sep
        self._value = []

    def set(self, value):
        self._value.extend(
            i.strip()
            for i in value.split(self._sep)
            if i.strip()
        )

    def get(self):
        return list(self._value)

class IniValueAttribute(IniAttribute):
    """ An INI attribute that is replaced by consecutive values. """

    def __init__(self, defval=None):
        IniAttribute.__init__(self)    
        self._value = defval

    def set(self, value):
        self._value = value

    def get(self):
        value = self._value

        if isinstance(value, str):
            if value.startswith('"') and value.endswith('"'):
                return value[1:-1]

        return value

class IniBoolAttribute(IniAttribute):
    """ Bool attribute. """

    def __init__(self, defval=False):
        IniAttribute.__init__(self)
        self._value = defval

    def set(self, value):
        bval = value.strip().lower() not in ("0", "false", "no", "off")
        self._value = bval

class IniAttributeSection(object):

    def update(self, section):
        for (key, value) in section:
            aname = "{0}".format(key.replace("-", "_"))
            attr = getattr(self, aname, None)

            if attr:
                attr.set(value)
            else:
                raise KeyError("Invalid attribute: {0}".format(key))

class IniSection(object):

    def __init__(self, factory, *args, **kwargs):
        self._factory = factory
        self._args = args
        self._kwargs = kwargs
        self._results = {}

    def update(self, section):
        for (key, value) in section:
            if key not in self._results:
                self._results[key] = self._factory(*self._args, **self._kwargs)
            
            self._results[key].set(value)

    def items(self):
        return list((i, j()) for (i, j) in self._results.items())

class DumpMixin(object):
    def dump(self):
        for i in sorted(dir(self)):
            v = getattr(self, i)
            if isinstance(v, IniAttribute):
                print("Value: {0}={1}".format(i, repr(v.get())))

class ConfigFileType(IniAttributeSection, DumpMixin):
    """ Represent the filetype """

    def __init__(self):
        IniAttributeSection.__init__(self)

        self.extensions = IniListAttribute()
        self.line_minlength = IniValueAttribute(80)
        self.line_padding = IniValueAttribute(1)

        self.firstline_start = IniValueAttribute("")
        self.firstline_end = IniValueAttribute("")
        self.firstline_prepad = IniValueAttribute(" ")
        self.firstline_postpad = IniValueAttribute(" ")
        self.firstline_filler = IniValueAttribute("#")
        self.firstline_center = IniBoolAttribute(True)

        self.lastline_start = IniValueAttribute("")
        self.lastline_end = IniValueAttribute("")
        self.lastline_prepad = IniValueAttribute(" ")
        self.lastline_postpad = IniValueAttribute(" ")
        self.lastline_filler = IniValueAttribute("#")
        self.lastline_center = IniBoolAttribute(True)

        self.midline_start = IniValueAttribute("")
        self.midline_end = IniValueAttribute("")
        self.midline_prepad = IniValueAttribute(" ")
        self.midline_postpad = IniValueAttribute(" ")
        self.midline_center = IniBoolAttribute(False)


class ConfigBlock(IniAttributeSection, DumpMixin):
    """ Represent a block. """

    def __init__(self):
        IniAttributeSection.__init__(self)

        self.start_pattern = IniValueAttribute("")
        self.end_pattern = IniValueAttribute("")
        self.start = IniValueAttribute("")
        self.end = IniValueAttribute("")

class ConfigAction(IniAttributeSection, DumpMixin):
    """ Represent an action. """

    def __init__(self):
        IniAttributeSection.__init__(self)

        self.filetype = IniListAttribute()
        self.text = IniValueAttribute("")
        self.block = IniValueAttribute("")

class ConfigTextFiles(IniSection):

    def __init__(self):
        IniSection.__init__(self, IniValueAttribute, "")


class Config(object):
    
    def __init__(self):
        self._filetypes = {}
        self._blocks = {}
        self._actions = {}
        self._textblocks = ConfigTextFiles()
        self._textfiles = ConfigTextFiles()

    def parse(self, filename):
        config = configparser.ConfigParser()
        config.read(filename)

        for section in config.sections():
            if section.startswith("filetype:"):
                filetypename = section[9:]
                if filetypename not in self._filetypes:
                    self._filetypes[filetypename] = ConfigFileType()
                self._filetypes[filetypename].update(config.items(section))
            elif section.startswith("block:"):
                blockname = section[6:]
                if blockname not in self._blocks:
                    self._blocks[blockname] = ConfigBlock()
                self._blocks[blockname].update(config.items(section))
            elif section.startswith("action:"):
                actionname = section[7:]
                if actionname not in self._actions:
                    self._actions[actionname] = ConfigAction()
                self._actions[actionname].update(config.items(section))
            elif section == "text-blocks":
                self._textblocks.update(config.items(section))
            elif section == "text-files":
                self._textfiles.update(config.items(section))
            else:
                raise KeyError("Unknown section: {0}".format("section"))

    def dump(self):
        for name in self._filetypes:
            print("FileType {0}".format(name))
            self._filetypes[name].dump()
        for name in self._blocks:
            print("Blocks {0}".format(name))
            self._blocks[name].dump()
        for name in self._actions:
            print("Actions {0}".format(name))
            self._actions[name].dump()


def determine_length(filetype, block, license):

    # First line
    firstline_len = (
        len(filetype.firstline_start.get()) +
        len(filetype.firstline_end.get()) +
        len(filetype.firstline_prepad.get()) + 
        len(filetype.firstline_postpad.get()) +
        len(block.start.get())
    )

    # Last line
    lastline_len = (
        len(filetype.lastline_start.get()) +
        len(filetype.lastline_end.get()) +
        len(filetype.lastline_prepad.get()) + 
        len(filetype.lastline_postpad.get()) +
        len(block.end.get())
    )

    # Middle lines
    liclen = max(len(line) for line in license) # Find largest line
    midline_len = (
        len(filetype.midline_start.get()) +
        len(filetype.midline_end.get()) +
        liclen
    )

    return max(firstline_len, midline_len, lastline_len, int(filetype.line_minlength.get()))

def apply_block(handle, filetype, block, license):
    # Apply to a file

    re_start = re.compile(block.start_pattern.get())
    re_end = re.compile(block.end_pattern.get())

    in_block = False
    for line in handle:
        if in_block:
            # Consume until we are out of the block
            if re_end.match(line):
                in_block = False
                generate_block(filetype, block, license)

            continue
        
        if re_start.match(line):
            in_block = True
            continue

        print(line, end="")
    if in_block:
        # Ended in the block
        generate_block(filetype, block, license)

def generate_block(filetype, block, license):
    length = determine_length(filetype, block, license)

    # First line
    firstline = [
        filetype.firstline_start.get(),
        "",
        filetype.firstline_prepad.get(),
        block.start.get(),
        filetype.firstline_postpad.get(),
        "",
        filetype.firstline_end.get()
    ]

    total = sum(len(part) for part in firstline)
    if total < length:
        char = filetype.firstline_filler.get()[0]
        filler = length - total

        if filetype.firstline_center.get():
            part = filler / 2
            firstline[1] = char * part
            filler -= part

        if filler > 0:
            firstline[5] = char * filler
            
    firstline = "".join(firstline)
    print(firstline)

    # Line padding
    padline = [
        filetype.midline_start.get(),
        "",
        filetype.midline_end.get()
    ]

    total = sum(len(part) for part in padline)
    if total < length and len(padline[2]):
        padline[1] = " " * (length - total)
    padline = "".join(padline)

    for i in range(int(filetype.line_padding.get())):
        print(padline)


    # Middle lines
    midline = [
        filetype.midline_start.get(),
        "",
        "",
        "",
        filetype.midline_end.get()
    ]

    for line in license:
        # reset padding area
        midline[1] = midline[3] = ""
        midline[2] = line

        # Only need adjusting if centering or have an ending
        if len(midline[4]) or filetype.midline_center.get():
            total = sum(len(part) for part in midline)
            if total < length:
                filler = length - total
                if filetype.midline_center.get() and (len(midline[4]) or len(midline[2])):
                    part = filler / 2
                    midline[1] = " " * part
                    filler -= part

                # Only add ending space if there is an ending
                if filler > 0 and len(midline[4]):
                    midline[3] = " " * filler

        line = "".join(midline)
        print(line)
           
    # Line padding

    for i in range(int(filetype.line_padding.get())):
        print(padline)

    # Last line
    lastline = [
        filetype.lastline_start.get(),
        "",
        filetype.lastline_prepad.get(),
        block.end.get(),
        filetype.lastline_postpad.get(),
        "",
        filetype.lastline_end.get()
    ]

    total = sum(len(part) for part in lastline)
    if total < length:
        char = filetype.lastline_filler.get()[0]
        filler = length - total

        if filetype.lastline_center.get():
            part = filler / 2
            lastline[1] = char * part
            filler -= part

        if filler > 0:
            lastline[5] = char * filler
            
    lastline = "".join(lastline)
    print(lastline)

        
c = Config()
c.parse("config.ini")
#c.dump()

test_license = [
    "Stop: This is a test license dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "",
    "1) Don't claim credit",
    "2) Don't share freely",
    "3) Feed me!"
]

with open("test.txt") as handle:
    apply_block(handle, c._filetypes["c"], c._blocks["license-c"], test_license)

