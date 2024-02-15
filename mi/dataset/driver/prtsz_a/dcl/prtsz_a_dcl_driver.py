#!/usr/bin/env python

"""
@package mi.dataset.driver.prtsz_a
@file mi-dataset/mi/dataset/driver/prtsz_a/dcl/prtsz_a_dcl_driver.py
@author Samuel Dahlberg
@brief DCL driver for the prtsz_a instrument
"""

from mi.dataset.dataset_driver import SimpleDatasetDriver
from mi.dataset.dataset_parser import DataSetDriverConfigKeys
from mi.dataset.parser.prtsz_a_dcl import PrtszADclParser


def parse(unused, source_file_path, particle_data_handler):
    """
    This is the method called by Uframe
    :param unused
    :param source_file_path This is the full path and filename of the file to be parsed
    :param particle_data_handler Java Object to consume the output of the parser
    :return particle_data_handler
    """

    with open(source_file_path, 'rb') as stream_handle:
        PrtszADclDriver(unused, stream_handle, particle_data_handler).processFileStream()

    return particle_data_handler


class PrtszADclDriver(SimpleDatasetDriver):
    """
        The prtsz_a driver class extends the SimpleDatasetDriver.
    """

    def __init__(self, unused, stream_handle, particle_data_handler):
        super(PrtszADclDriver, self).__init__(unused, stream_handle, particle_data_handler)

    def _build_parser(self, stream_handle):
        parser_config = {
            DataSetDriverConfigKeys.PARTICLE_MODULE: 'mi.dataset.parser.prtsz_a_dcl',
            DataSetDriverConfigKeys.PARTICLE_CLASS: 'PrtszADataParticle'}

        parser = PrtszADclParser(parser_config, stream_handle, self._exception_callback)

        return parser
