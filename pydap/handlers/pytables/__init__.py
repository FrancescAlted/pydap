"""Pydap handler for HDF5 files using PyTables."""

# TODO: add attributes

import os
import re
import time
from stat import ST_MTIME
from email.utils import formatdate

import tables
from pkg_resources import get_distribution

from pydap.model import DatasetType, GridType, BaseType, StructureType, SequenceType
from pydap.handlers.lib import BaseHandler
from pydap.exceptions import OpenFileError


class PyTablesHandler(BaseHandler):

    """A simple handler for HDF5 files based on PyTables."""

    __version__ = get_distribution("pydap.handlers.pytables").version
    extensions = re.compile(r"^.*\.h5$", re.IGNORECASE)

    def __init__(self, filepath):
        BaseHandler.__init__(self)

        try:
            self.fp = tables.open_file(filepath, 'r')
        except Exception as exc:
            message = 'Unable to open file %s: %s' % (filepath, exc)
            raise OpenFileError(message)

        self.additional_headers.append(
            ('Last-modified', (
                formatdate(
                    time.mktime(
                        time.localtime(os.stat(filepath)[ST_MTIME]))))))

        # build dataset
        name = os.path.split(filepath)[1]
        self.dataset = DatasetType(name, attributes={
            "NC_GLOBAL": {},
        })
        build_dataset(self.dataset, self.fp, self.fp.root)


def build_dataset(target, fp, node):
    """Recursively build a dataset, mapping groups to structures."""
    for node in fp.list_nodes(node):
        if isinstance(node, tables.Group):
            target[node._v_name] = StructureType(node._v_name)
            build_dataset(target[node._v_name], fp, node)
        elif isinstance(node, tables.Array):
            target[node._v_name] = BaseType(
                node._v_name, node, None)
        elif isinstance(node, tables.Table):
            sequence = target[node._v_name] = SequenceType(node._v_name)
            for name in node.colnames:
                sequence[name] = BaseType(name, node.coldtypes[name])
            sequence.data = node.read()


if __name__ == "__main__":
    import sys
    from werkzeug.serving import run_simple

    application = PyTablesHandler(sys.argv[1])
    run_simple('localhost', 8001, application, use_reloader=True)
