import click



@click.group()
def main():
    """MXX Configuration Tool"""
    pass

from mxx.cfg_tool.app import app # noqa
from mxx.cfg_tool.cfg import cfg # noqa
main.add_command(app)
main.add_command(cfg)

