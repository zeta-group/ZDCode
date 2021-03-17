import argparse
import os
import sys

try:
    import zdcode
    import zdcode.zake as zake
    from zdcode.bundle import Bundle

except ImportError:
    import __init__ as zdcode
    import zake
    from bundle import Bundle


def main():
    return main_zake()


def main_zake():
    return zake.main(print_status_code=False)
