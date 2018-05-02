"""Pydap handler for Array Storage files."""

import re
import json
import os
from pkg_resources import get_distribution

import numpy as np

from pydap.model import DatasetType, GridType, BaseType
from pydap.handlers.lib import BaseHandler
from pydap.exceptions import OpenFileError

from kisters.water.array_storage.physical_storage.dm.types import Dimension
from kisters.water.array_storage.physical_storage.sadp.map_storage_configuration import MapStorageConfigurationStore
from kisters.water.array_storage.physical_storage.service.service_manager import ServiceManager


class ArrayStorageHandler(BaseHandler):

    """A simple handler for NetCDF files.
    Here's a standard dataset for testing sequential data:
    """

    pydap_version = get_distribution("pydap").version
    extensions = re.compile(r"^.*\.as$", re.IGNORECASE)

    def __init__(self, filepath):
        BaseHandler.__init__(self)
        self.filepath = filepath
        try:
            with open(filepath) as fp:
                config = json.loads(fp.read())
        except Exception as exc:
            message = 'Unable to open file %s: %s' % (filepath, exc)
            raise OpenFileError(message)

        msconfig = MapStorageConfigurationStore(config)
        self.service = ServiceManager(msconfig)

        # Create a group and an array (just for testing purposes)
        group = self.service.get_group('mem', "/")
        array = self.service.create_array('mem', os.path.join(group.path, "array"),
                                          [Dimension(10, None, None), Dimension(10, None, None),
                                           Dimension(10, None, None)], None, None)

        # build dap dataset
        self.dataset = DatasetType('mem', attributes={})
        # add grids
        self.dataset['array'] = grid = GridType('array', attributes=None)
        # add array
        # grid['array'] = BaseType('array', self.service.get_data("mem", "/array", (slice(None), slice(None), slice(None))),
        #                          None, attributes=None)
        grid['array'] = BaseType('array', LazyAdapter(self.service, "mem", "array", "/array", array),
                                 None, attributes=None)


class LazyAdapter:
    def __init__(self, service, store, name, path, var):
        self.service = service
        self.store = store
        self.name = name
        self.path = path
        #var = source[self.path]
        self.var = self.service.get_data(self.store, self.path, (slice(None), slice(None), slice(None)))
        self.dtype = np.dtype(self.var.dtype)
        self.datatype = self.var.dtype
        self._shape = self.var.shape
        self.ndim = len(self._shape)
        self.size = np.prod(self._shape)
        self._attributes = None  # not implemented yet
        return

    def chunking(self):
        return 'contiguous'

    def filters(self):
        return None

    def get_var_chunk_cache(self):
        raise NotImplementedError('get_var_chunk_cache is not implemented')

    def __getattr__(self, name):
        return {} # Not implemented yet

    def getValue(self):
        self.service.get_data(self.store, self.path, (slice(None), slice(None), slice(None)))

    def __array__(self):
        self.service.get_data(self.store, self.path, (slice(None), slice(None), slice(None)))

    def __getitem__(self, key):
        self.service.get_data(self.store, self.path, (slice(None), slice(None), slice(None)))

    @property
    def shape(self):
        return self._shape

    def __len__(self):
        if not self.shape:
            raise TypeError('len() of unsized object')
        else:
            return self.shape[0]
