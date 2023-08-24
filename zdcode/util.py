"""Miscellaneous utilities used by ZDCode internally."""
import random
import string


def stringify(content):
    """Adds quotes around a string."""
    if isinstance(content, str):
        if len(content) > 1 and content[0] in "'\"" and content[-1] == content[0]:
            return content

        return '"' + repr(content)[1:-1] + '"'

    return repr(content)


def unstringify(content):
    """Removes quotes around a string."""
    if content[0] in "'\"" and content[-1] == content[0] and len(content) > 1:
        return content[1:-1]

    return content


def make_id(length=30):
    """Generates and returns a random ID.

    This generated ID can be stored in a ZDCode object
    to allow namespace compatibility between multiple
    ZDCode mods."""
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


def decorate(obj, indent=4):
    """Get the object's compiled DECORATE code."""
    return obj.to_decorate().to_string(indent)


class TextNode:
    """A recursive line-wise text data structure."""

    def __init__(self, lines=(), indent=1):
        self.lines = list(lines)
        self.indent = indent

    def add_line(self, line):
        """Add a line to this TextNode."""
        self.lines.append(line)

    def __str__(self):
        return "\n".join(
            "\n".join("\t" * self.indent + x for x in str(l).split("\n"))
            for l in self.lines
        )

    def __len__(self):
        return len(str(self))

    def __getitem__(self, ind):
        return self.lines[ind]

    def to_string(self, tab_size=4):
        """Convert this to a string with a custom tab size."""
        return "\n".join(str(l) for l in self.lines).replace("\t", " " * tab_size)
