#!/usr/bin/env python

"""
@file ion/services/mi/drivers/satlantic_par/test/test_satlantic_par.py
@author Steve Foley, Ronald Ronquillo
@test ion.services.mi.drivers.satlantic_par
Unit test suite to test Satlantic PAR sensor
"""

import time
import json
import random
from nose.plugins.attrib import attr
from mock import Mock
from mi.core.instrument.instrument_driver import ResourceAgentState

from mi.core.log import get_logger
log = get_logger()

from mi.core.instrument.instrument_driver import DriverConnectionState, DriverEvent
from mi.core.instrument.instrument_driver import ConfigMetadataKey, DriverConfigKey
from mi.core.instrument.data_particle import DataParticleKey, DataParticleValue
from mi.core.instrument.chunker import StringChunker
from mi.core.instrument.protocol_cmd_dict import CommandDictKey
from mi.core.instrument.protocol_param_dict import ParameterDictKey

from mi.idk.unit_test import DriverTestMixin, ParameterTestConfigKey, InstrumentDriverTestCase

from mi.core.exceptions import InstrumentCommandException, InstrumentParameterException, SampleException

from mi.idk.unit_test import InstrumentDriverUnitTestCase, InstrumentDriverIntegrationTestCase
from mi.idk.unit_test import InstrumentDriverQualificationTestCase, AgentCapabilityType

from mi.instrument.satlantic.par_ser_600m.driver import Commands, DataParticleType, SatlanticPARInstrumentProtocol
from mi.instrument.satlantic.par_ser_600m.driver import PARProtocolState, PARProtocolEvent, PARCapability, Parameter
from mi.instrument.satlantic.par_ser_600m.driver import ScheduledJob, EOLN, Prompt, SatlanticPARConfigParticle
from mi.instrument.satlantic.par_ser_600m.driver import PARParticle, PARParticleNew
from mi.instrument.satlantic.par_ser_600m.driver import PARDataKey, SatlanticPARConfigParticleKey
from mi.instrument.satlantic.par_ser_600m.driver import PARDataKeyNew
from mi.instrument.satlantic.par_ser_600m.driver import SatlanticPARInstrumentDriver, EngineeringParameter


InstrumentDriverTestCase.initialize(
    driver_module='mi.instrument.satlantic.par_ser_600m.driver',
    driver_class="SatlanticPARInstrumentDriver",

    instrument_agent_resource_id='satlantic_par_ser_600m_ooicore',
    instrument_agent_name='satlantic_par_ser_600m_agent',
    instrument_agent_packet_config=DataParticleType(),
    driver_startup_config={
        DriverConfigKey.PARAMETERS: {
            Parameter.MAXRATE: 1}}
)


# SATPAR4278190306,49.02,2157023616,171
VALID_SAMPLE = "SATPAR4278190306,49.02,2157023616,171\r\n"
INVALID_SAMPLE = "SATPAR4278190306,49.02,2157023616,172\r\n"
VALID_SAMPLE_NEW = "SATPRL1017,276.415,15.456,77.1,11.3,43.9,LOG,372649,0.090978906,1.8937789,252,-47,1022,2137,0.939,0,114\r\n"


# Make tests verbose and provide stdout
# bin/nosetests -s -v ion/services/mi/drivers/test/test_satlantic_par.py
# All unit tests: add "-a UNIT" to end, integration add "-a INT"
# Test device is at 10.180.80.173, port 2101

# these values checkout against the sample above
valid_particle = [{DataParticleKey.VALUE_ID: PARDataKey.SERIAL_NUM, DataParticleKey.VALUE: '4278190306'},
                  {DataParticleKey.VALUE_ID: PARDataKey.TIMER, DataParticleKey.VALUE: 49.02},
                  {DataParticleKey.VALUE_ID: PARDataKey.COUNTS, DataParticleKey.VALUE: 2157023616}]

valid_particle_new = \
    [{DataParticleKey.VALUE_ID: PARDataKeyNew.SERIAL_NUM, DataParticleKey.VALUE: '1017'},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.TIMER, DataParticleKey.VALUE: 276.415},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.PAR, DataParticleKey.VALUE: 15.456},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.PITCH, DataParticleKey.VALUE: 77.1},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.ROLL, DataParticleKey.VALUE: 11.3},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.TEMP, DataParticleKey.VALUE: 43.9},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.COUNTS, DataParticleKey.VALUE: 372649},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.V_IN, DataParticleKey.VALUE: 0.090978906},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.V_OUT, DataParticleKey.VALUE: 1.8937789},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.X_AXIS, DataParticleKey.VALUE: 252},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.Y_AXIS, DataParticleKey.VALUE: -47},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.Z_AXIS, DataParticleKey.VALUE: 1022},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.T_COUNTS, DataParticleKey.VALUE: 2137},
     {DataParticleKey.VALUE_ID: PARDataKeyNew.T_VOLTS, DataParticleKey.VALUE: 0.939}]

bad_checksum_particle = [{DataParticleKey.VALUE_ID: PARDataKey.SERIAL_NUM, DataParticleKey.VALUE: '4278190306'},
                         {DataParticleKey.VALUE_ID: PARDataKey.TIMER, DataParticleKey.VALUE: 49.02},
                         {DataParticleKey.VALUE_ID: PARDataKey.COUNTS, DataParticleKey.VALUE: 2157023616}]

VALID_CONFIG = "Maximum Frame Rate: 0.125 Hz\r\n" + \
               "Telemetry Baud Rate: 19200 bps"

valid_config_particle = [{DataParticleKey.VALUE_ID: SatlanticPARConfigParticleKey.BAUD_RATE, DataParticleKey.VALUE: 19200},
                  {DataParticleKey.VALUE_ID: SatlanticPARConfigParticleKey.MAX_RATE, DataParticleKey.VALUE: 0.125},
                  {DataParticleKey.VALUE_ID: SatlanticPARConfigParticleKey.SERIAL_NUM, DataParticleKey.VALUE: '4278190306'},
                  {DataParticleKey.VALUE_ID: SatlanticPARConfigParticleKey.FIRMWARE, DataParticleKey.VALUE: '1.0.0'},
                  {DataParticleKey.VALUE_ID: SatlanticPARConfigParticleKey.TYPE, DataParticleKey.VALUE: 'SATPAR'}]

port_timestamp = 3555423720.711772
driver_timestamp = 3555423722.711772

TIMEOUT = 30

class PARMixin(DriverTestMixin):
    """
    Mixin class used for storing data particle constance and common data assertion methods.
    """
    SatlanticPARInstrumentDriver = SatlanticPARInstrumentDriver

    # Create some short names for the parameter test config
    TYPE      = ParameterTestConfigKey.TYPE
    READONLY  = ParameterTestConfigKey.READONLY
    STARTUP   = ParameterTestConfigKey.STARTUP
    DA        = ParameterTestConfigKey.DIRECT_ACCESS
    VALUE     = ParameterTestConfigKey.VALUE
    REQUIRED  = ParameterTestConfigKey.REQUIRED
    DEFAULT   = ParameterTestConfigKey.DEFAULT
    STATES    = ParameterTestConfigKey.STATES

    ###
    #  Parameter and Type Definitions
    ###

    _driver_parameters = {
        Parameter.MAXRATE: {TYPE: float, READONLY: False, DA: True, STARTUP: True, VALUE: 4, REQUIRED: True},
        Parameter.FIRMWARE: {TYPE: str, READONLY: True, DA: False, STARTUP: False, VALUE: '1.0.0', REQUIRED: False},
        Parameter.SERIAL: {TYPE: str, READONLY: True, DA: False, STARTUP: False, VALUE: '4278190306', REQUIRED: False},
        Parameter.ACQUIRE_STATUS_INTERVAL: {TYPE: str, READONLY: False, DA: False, STARTUP: True, VALUE: '00:00:00', REQUIRED: True}
    }

    _driver_capabilities = {
        # capabilities defined in the IOS
        PARProtocolEvent.DISCOVER: {STATES: [PARProtocolState.UNKNOWN]},
        PARProtocolEvent.ACQUIRE_SAMPLE: {STATES: [PARProtocolState.COMMAND]},
        PARProtocolEvent.START_AUTOSAMPLE: {STATES: [PARProtocolState.COMMAND]},
        PARProtocolEvent.STOP_AUTOSAMPLE: {STATES: [PARProtocolState.AUTOSAMPLE]},
        PARProtocolEvent.ACQUIRE_STATUS: {STATES: [PARProtocolState.COMMAND, PARProtocolState.AUTOSAMPLE]}
    }

    _config_parameters = {
        # Parameters defined in the IOS
        SatlanticPARConfigParticleKey.BAUD_RATE: {TYPE: int, READONLY: True, DA: True, STARTUP: False, VALUE: 19200, REQUIRED: True},
        SatlanticPARConfigParticleKey.MAX_RATE: {TYPE: float, READONLY: False, DA: True, STARTUP: True, VALUE: 0.5, REQUIRED: True},
        SatlanticPARConfigParticleKey.SERIAL_NUM: {TYPE: str, READONLY: True, DA: False, STARTUP: False, VALUE: '4278190306', REQUIRED: True},
        SatlanticPARConfigParticleKey.FIRMWARE: {TYPE: str, READONLY: True, DA: False, STARTUP: False, VALUE: '1.0.0', REQUIRED: True},
        SatlanticPARConfigParticleKey.TYPE: {TYPE: str, READONLY: True, DA: False, STARTUP: False, VALUE: 'SATPAR', REQUIRED: True},
    }

    _sample_parameters = {
        PARDataKey.SERIAL_NUM: {TYPE: str, VALUE: '4278190306', REQUIRED: True},
        PARDataKey.COUNTS: {TYPE: int, VALUE: 2157023616, REQUIRED: True},
        PARDataKey.TIMER: {TYPE: float, VALUE: 49.02, REQUIRED: True}
    }

    _sample_parameters_new = {
        PARDataKeyNew.SERIAL_NUM: {TYPE: str, VALUE: '1017', REQUIRED: True},
        PARDataKeyNew.TIMER: {TYPE: float, VALUE: 276.415, REQUIRED: True},
        PARDataKeyNew.PAR: {TYPE: float, VALUE: 15.456, REQUIRED: True},
        PARDataKeyNew.PITCH: {TYPE: float, VALUE: 77.1, REQUIRED: True},
        PARDataKeyNew.ROLL: {TYPE: float, VALUE: 11.3, REQUIRED: True},
        PARDataKeyNew.TEMP: {TYPE: float, VALUE: 43.9, REQUIRED: True},
        PARDataKeyNew.COUNTS: {TYPE: int, VALUE: 372649, REQUIRED: True},
        PARDataKeyNew.V_IN: {TYPE: float, VALUE: 0.090978906, REQUIRED: True},
        PARDataKeyNew.V_OUT: {TYPE: float, VALUE: 1.8937789, REQUIRED: True},
        PARDataKeyNew.X_AXIS: {TYPE: int, VALUE: 252, REQUIRED: True},
        PARDataKeyNew.Y_AXIS: {TYPE: int, VALUE: -47, REQUIRED: True},
        PARDataKeyNew.Z_AXIS: {TYPE: int, VALUE: 1022, REQUIRED: True},
        PARDataKeyNew.T_COUNTS: {TYPE: int, VALUE: 2137, REQUIRED: True},
        PARDataKeyNew.T_VOLTS: {TYPE: float, VALUE: 0.939, REQUIRED: True}
    }

    _capabilities = {
        PARProtocolState.UNKNOWN:      [PARProtocolEvent.DISCOVER],

        PARProtocolState.COMMAND:      [PARProtocolEvent.GET,
                                        PARProtocolEvent.SET,
                                        PARProtocolEvent.START_DIRECT,
                                        PARProtocolEvent.START_AUTOSAMPLE,
                                        PARProtocolEvent.ACQUIRE_SAMPLE,
                                        PARProtocolEvent.SCHEDULED_ACQUIRE_STATUS,
                                        PARProtocolEvent.ACQUIRE_STATUS],

        PARProtocolState.AUTOSAMPLE:   [PARProtocolEvent.GET,
                                        PARProtocolEvent.STOP_AUTOSAMPLE,
                                        PARProtocolEvent.SCHEDULED_ACQUIRE_STATUS],

        PARProtocolState.DIRECT_ACCESS: [PARProtocolEvent.STOP_DIRECT,
                                         PARProtocolEvent.EXECUTE_DIRECT]
    }

    ###
    #   Driver Parameter Methods
    ###
    def assert_driver_parameters(self, current_parameters, verify_values=False):
        """
        Verify that all driver parameters are correct and potentially verify values.
        @param current_parameters: driver parameters read from the driver instance
        @param verify_values: should we verify values against definition?
        """
        self.assert_parameters(current_parameters, self._driver_parameters, verify_values)

    def assert_config_parameters(self, current_parameters, verify_values=False):
        """
        Verify that all driver parameters are correct and potentially verify values.
        @param current_parameters: driver parameters read from the driver instance
        @param verify_values: should we verify values against definition?
        """
        self.assert_data_particle_keys(SatlanticPARConfigParticleKey, self._config_parameters)
        self.assert_data_particle_header(current_parameters, DataParticleType.CONFIG)
        self.assert_data_particle_parameters(current_parameters, self._config_parameters, verify_values)

    def assert_particle_sample(self, data_particle, verify_values=False):
        """
        Verify sample particle
        @param data_particle:  SBE16DataParticle data particle
        @param verify_values:  bool, should we verify parameter values
        """
        self.assert_data_particle_keys(PARDataKey, self._sample_parameters)
        self.assert_data_particle_header(data_particle, DataParticleType.PARSED)
        self.assert_data_particle_parameters(data_particle, self._sample_parameters, verify_values)

    def assert_particle_sample_new(self, data_particle, verify_values=False):
        """
        Verify sample particle
        @param data_particle:  SBE16DataParticle data particle
        @param verify_values:  bool, should we verify parameter values
        """
        self.assert_data_particle_keys(PARDataKeyNew, self._sample_parameters_new)
        self.assert_data_particle_header(data_particle, DataParticleType.PARSED)
        self.assert_data_particle_parameters(data_particle, self._sample_parameters_new, verify_values)

@attr('UNIT', group='mi')
class SatlanticParProtocolUnitTest(InstrumentDriverUnitTestCase, PARMixin):
    def test_driver_enums(self):
        """
        Verify that all driver enumeration has no duplicate values that might cause confusion.  Also
        do a little extra validation for the Capabilities
        """
        self.assert_enum_has_no_duplicates(Commands())
        self.assert_enum_has_no_duplicates(ScheduledJob())
        self.assert_enum_has_no_duplicates(DataParticleType())
        self.assert_enum_has_no_duplicates(PARProtocolState())
        self.assert_enum_has_no_duplicates(PARProtocolEvent())
        self.assert_enum_has_no_duplicates(Parameter())
        self.assert_enum_has_no_duplicates(Prompt())

        # Test capabilities for duplicates, them verify that capabilities is a subset of protocol events
        self.assert_enum_has_no_duplicates(PARCapability())
        self.assert_enum_complete(PARCapability(), PARProtocolEvent())

    def test_driver_schema(self):
        """
        get the driver schema and verify it is configured properly
        """
        driver = self.SatlanticPARInstrumentDriver(self._got_data_event_callback)
        self.assert_driver_schema(driver, self._driver_parameters, self._driver_capabilities)

    def test_driver_protocol_filter_capabilities(self):
        """
        Iterate through available capabilities, and verify that they can pass successfully through the filter.
        Test silly made up capabilities to verify they are blocked by filter.
        """
        mock_callback = Mock(spec="PortAgentClient")
        protocol = SatlanticPARInstrumentProtocol(mock_callback)
        driver_capabilities = PARCapability().list()
        test_capabilities = PARCapability().list()

        # Add a bogus capability that will be filtered out.
        test_capabilities.append("BOGUS_CAPABILITY")

        # Verify "BOGUS_CAPABILITY was filtered out
        self.assertEqual(sorted(driver_capabilities), sorted(protocol._filter_capabilities(test_capabilities)))

    def test_chunker(self):
        """
        Tests the chunker
        """
        # This will want to be created in the driver eventually...
        chunker = StringChunker(SatlanticPARInstrumentProtocol.sieve_function)

        self.assert_chunker_sample(chunker, VALID_SAMPLE)
        self.assert_chunker_sample(chunker, VALID_SAMPLE_NEW)
        self.assert_chunker_sample(chunker, VALID_CONFIG)

        self.assert_chunker_fragmented_sample(chunker, VALID_SAMPLE)
        self.assert_chunker_fragmented_sample(chunker, VALID_SAMPLE_NEW)
        self.assert_chunker_fragmented_sample(chunker, VALID_CONFIG)

        self.assert_chunker_combined_sample(chunker, VALID_SAMPLE)
        self.assert_chunker_combined_sample(chunker, VALID_SAMPLE_NEW)
        self.assert_chunker_combined_sample(chunker, VALID_CONFIG)

        self.assert_chunker_sample_with_noise(chunker, VALID_SAMPLE)
        self.assert_chunker_sample_with_noise(chunker, VALID_SAMPLE_NEW)
        self.assert_chunker_sample_with_noise(chunker, VALID_CONFIG)

    def test_corrupt_data_structures(self):
        """
        Verify when generating the particle, if the particle is corrupt, an exception is raised
        """
        log.debug('test_corrupt_data_structures: %s', VALID_SAMPLE.replace('A', 'B'))
        particle = PARParticle(VALID_SAMPLE.replace('A', 'B'), port_timestamp=port_timestamp)
        with self.assertRaises(SampleException):
            obj = particle.generate()
            self.assertNotEqual(obj[DataParticleKey.QUALITY_FLAG], DataParticleValue.OK)

    def test_sample_format(self):
        """
        Verify driver can get sample data out in a reasonable format.
        Parsed is all we care about...raw is tested in the base DataParticle tests
        """
        # construct the expected particle
        expected_particle = {DataParticleKey.PKT_FORMAT_ID: DataParticleValue.JSON_DATA, DataParticleKey.PKT_VERSION: 1,
                             DataParticleKey.STREAM_NAME: DataParticleType.PARSED,
                             DataParticleKey.PORT_TIMESTAMP: port_timestamp,
                             DataParticleKey.DRIVER_TIMESTAMP: driver_timestamp,
                             DataParticleKey.PREFERRED_TIMESTAMP: DataParticleKey.PORT_TIMESTAMP,
                             DataParticleKey.QUALITY_FLAG: DataParticleValue.OK,
                             DataParticleKey.VALUES: valid_particle}

        self.compare_parsed_data_particle(PARParticle, VALID_SAMPLE, expected_particle)
        expected_particle[DataParticleKey.VALUES] = valid_particle_new
        self.compare_parsed_data_particle(PARParticleNew, VALID_SAMPLE_NEW, expected_particle)

    def test_bad_checksum_sample_format(self):
        """
        Verify driver can get sample data out in a reasonable format.
        Parsed is all we care about...raw is tested in the base DataParticle tests
        """
        # construct the expected particle
        expected_particle = {
            DataParticleKey.PKT_FORMAT_ID: DataParticleValue.JSON_DATA,
            DataParticleKey.PKT_VERSION: 1,
            DataParticleKey.STREAM_NAME: DataParticleType.PARSED,
            DataParticleKey.PORT_TIMESTAMP: port_timestamp,
            DataParticleKey.DRIVER_TIMESTAMP: driver_timestamp,
            DataParticleKey.PREFERRED_TIMESTAMP: DataParticleKey.PORT_TIMESTAMP,
            DataParticleKey.QUALITY_FLAG: DataParticleValue.CHECKSUM_FAILED,
            DataParticleKey.VALUES: bad_checksum_particle
        }

        self.compare_parsed_data_particle(PARParticle, INVALID_SAMPLE, expected_particle)

    def compare_parsed_data_particle_override(self, particle_type, raw_input, happy_structure):
        """
        Compare a data particle created with the raw input string to the structure that should be generated.

        @param particle_type The data particle class to create
        @param raw_input The input string that is instrument-specific
        @param happy_structure The structure that should result from parsing the
            raw input during DataParticle creation
        """
        port_timestamp = happy_structure[DataParticleKey.PORT_TIMESTAMP]
        if DataParticleKey.INTERNAL_TIMESTAMP in happy_structure:
            internal_timestamp = happy_structure[DataParticleKey.INTERNAL_TIMESTAMP]
            test_particle = particle_type(raw_input, port_timestamp=port_timestamp,
                                          internal_timestamp=internal_timestamp)
        else:
            test_particle = particle_type("4278190306", "1.0.0", raw_input, port_timestamp=port_timestamp)

        parsed_result = test_particle.generate()

        driver_time = parsed_result[DataParticleKey.DRIVER_TIMESTAMP]
        happy_structure[DataParticleKey.DRIVER_TIMESTAMP] = driver_time

        self.assertEqual(parsed_result, happy_structure)

    def test_config_format(self):
        """
        Verify driver can get sample data out in a reasonable format.
        Parsed is all we care about...raw is tested in the base DataParticle tests
        """
        # construct the expected particle
        expected_particle = {
            DataParticleKey.PKT_FORMAT_ID: DataParticleValue.JSON_DATA,
            DataParticleKey.PKT_VERSION: 1,
            DataParticleKey.STREAM_NAME: DataParticleType.CONFIG,
            DataParticleKey.PORT_TIMESTAMP: port_timestamp,
            DataParticleKey.DRIVER_TIMESTAMP: driver_timestamp,
            DataParticleKey.PREFERRED_TIMESTAMP: DataParticleKey.PORT_TIMESTAMP,
            DataParticleKey.QUALITY_FLAG: DataParticleValue.OK,
            DataParticleKey.VALUES: valid_config_particle
        }

        self.compare_parsed_data_particle_override(SatlanticPARConfigParticle, VALID_CONFIG, expected_particle)

    def test_capabilities(self):
        """
        Verify the FSM reports capabilities as expected.  All states defined in this dict must
        also be defined in the protocol FSM.
        """

        driver = SatlanticPARInstrumentDriver(self._got_data_event_callback)
        self.assert_capabilities(driver, self._capabilities)

    def test_got_data(self):
        """
        Verify sample data passed through the got data method produces the correct data particles
        """
        # Create and initialize the instrument driver with a mock port agent
        driver = SatlanticPARInstrumentDriver(self._got_data_event_callback)
        self.assert_initialize_driver(driver)

        self.assert_raw_particle_published(driver, True)

        # Start validating data particles
        self.assert_particle_published(driver, VALID_SAMPLE, self.assert_particle_sample, True)
        self.assert_particle_published(driver, VALID_SAMPLE_NEW, self.assert_particle_sample_new, True)




@attr('INT', group='mi')
class SatlanticParProtocolIntegrationTest(InstrumentDriverIntegrationTestCase, PARMixin):

    def test_parameters(self):
        """
        Verify that we can set the parameters

        1. Cannot set read only parameters
        2. Can set read/write parameters
        """
        self.assert_initialize_driver(PARProtocolState.COMMAND)

        #test read/write parameter good values
        self.assert_set(Parameter.MAXRATE, 2)
        self.assert_set(Parameter.MAXRATE, 0.0)
        self.assert_set(Parameter.MAXRATE, 1.0)
        self.assert_set(Parameter.MAXRATE, 00.50)

        #test read/write parameter out of range values
        self.assert_set_exception(Parameter.MAXRATE, 20)
        self.assert_set_exception(Parameter.MAXRATE, -20)
        self.assert_set_exception(Parameter.MAXRATE, 1.5)
        self.assert_set_exception(Parameter.MAXRATE, 7)
        self.assert_set_exception(Parameter.MAXRATE, 13)

        #test read only parameter
        self.assert_set_exception(Parameter.FIRMWARE, '1.0.1')
        self.assert_set_exception(Parameter.SERIAL, '4278190307')

    def test_metadata_generation(self):
        """
        Verify the driver generates metadata information
        """
        self.assert_initialize_driver()

        self.assert_metadata_generation(instrument_params=Parameter.list(), commands=PARCapability.list())

        # check one to see that the file is loading data from somewhere.
        json_result = self.driver_client.cmd_dvr("get_config_metadata")
        result = json.loads(json_result)

        params = result[ConfigMetadataKey.PARAMETERS]
        self.assertEqual(params[Parameter.MAXRATE][ParameterDictKey.DISPLAY_NAME], "Max Rate")

        cmds = result[ConfigMetadataKey.COMMANDS]
        self.assertEqual(cmds[PARCapability.ACQUIRE_SAMPLE][CommandDictKey.DISPLAY_NAME], "Acquire Sample")

    def test_startup_params(self):
        """
        Verify that startup parameters are applied correctly. Generally this
        happens in the driver discovery method.
        """

        # Explicitly verify these values after discover.  They should match
        # what the startup values should be
        get_values = {
            Parameter.MAXRATE: 4,
            Parameter.FIRMWARE: '1.0.0',
            Parameter.SERIAL: '4278190306',
            Parameter.ACQUIRE_STATUS_INTERVAL: '00:00:00'
        }

        # Change the values of these parameters to something before the
        # driver is reinitialized.  They should be blown away on reinit.
        new_values = {
            Parameter.MAXRATE: 0.5,
            Parameter.ACQUIRE_STATUS_INTERVAL: '00:00:25'
        }

        self.assert_initialize_driver()
        self.assert_startup_parameters(self.assert_driver_parameters, new_values, get_values)

        # Change values and try again
        self.assert_set_bulk(new_values)
        self.assert_startup_parameters(self.assert_driver_parameters)


    def test_acquire_status(self):
        """
        Test acquire status command and events.

        1. initialize the instrument to COMMAND state
        2. command the instrument to ACQUIRE STATUS
        3. verify the status particle coming in
        """
        self.assert_initialize_driver(PARProtocolState.COMMAND)
        self.assert_driver_command(PARProtocolEvent.ACQUIRE_STATUS, state=PARProtocolState.COMMAND, delay=5)
        self.assert_async_particle_generation(DataParticleType.CONFIG, self.assert_config_parameters)

    def test_acquire_sample(self):
        """
        Test acquire sample command and events.

        1. initialize the instrument to COMMAND state
        2. command the instrument to ACQUIRE SAMPLE
        3. verify the particle coming in
        """
        self.assert_initialize_driver(PARProtocolState.COMMAND)
        self.assert_driver_command(PARProtocolEvent.ACQUIRE_SAMPLE, state=PARProtocolState.COMMAND, delay=5)
        self.assert_async_particle_generation(DataParticleType.PARSED, self.assert_particle_sample)

    def test_command_autosample(self, sleep_time=15):
        """
        Test autosample command and events.

        1. initialize the instrument to COMMAND state
        2. command the instrument to AUTOSAMPLE
        3. verify the particle coming in
        4. command the instrument back to COMMAND state
        """
        self.assert_initialize_driver(PARProtocolState.COMMAND)
        self.assert_driver_command(PARProtocolEvent.START_AUTOSAMPLE, state=PARProtocolState.AUTOSAMPLE, delay=3)
        time.sleep(sleep_time)
        self.assert_async_particle_generation(DataParticleType.PARSED, self.assert_particle_sample, particle_count=40)
        self.assert_driver_command(PARProtocolEvent.STOP_AUTOSAMPLE, state=PARProtocolState.COMMAND, delay=3)

    # @unittest.skip('temp disable')  # Keep: This is a useful stress test
    def test_command_autosample_multiple(self):
        """
        Similar to the test_command_autosample above, but this will test getting in & out of sampling at
        all possible maxrate values with a random amount of sample wait time between
        """
        timeout = 10*60
        count = 0
        starttime = time.time()
        startstamp = time.strftime("%H:%M:%S", time.gmtime())
        maxrates = [[0, 1], [0.125, 9], [0.5, 3], [1, 2], [2, 1], [4, 1], [8, 1], [10, 1], [12, 1]]

        self.assert_initialize_driver(PARProtocolState.COMMAND)

        while True:
            random.shuffle(maxrates)
            for maxrate, min_sleep in maxrates:
                sleep_time = random.uniform(min_sleep, 15)
                count += 1
                log.debug('START test_command_autosample: #%s maxrate=%s, %s, sleep=%s',
                          count, maxrate, time.strftime("%H:%M:%S", time.gmtime()), sleep_time)
                self.assert_set(Parameter.MAXRATE, maxrate)

                self.assert_driver_command(PARProtocolEvent.ACQUIRE_STATUS, state=PARProtocolState.COMMAND, delay=5)
                self.assert_async_particle_generation(DataParticleType.CONFIG, self.assert_config_parameters)

                self.assert_driver_command(PARProtocolEvent.START_AUTOSAMPLE,
                                           state=PARProtocolState.AUTOSAMPLE, delay=3)
                time.sleep(sleep_time)
                self.assert_async_particle_generation(DataParticleType.PARSED, self.assert_particle_sample)
                self.assert_driver_command(PARProtocolEvent.STOP_AUTOSAMPLE, state=PARProtocolState.COMMAND, delay=3)

            if time.time() > starttime + timeout:
                break

        self.assert_set(Parameter.MAXRATE, 4, no_get=True)
        log.debug('FINISHED test_command_autosample: #%s, start:%s/end:%s, timeout=%s',
                  count, startstamp, time.strftime("%H:%M:%S", time.gmtime()), timeout)

    def test_direct_access(self):
        """
        Verify the driver can enter/exit the direct access state
        """
        self.assert_initialize_driver(PARProtocolState.COMMAND)

        self.assert_state_change(PARProtocolState.COMMAND, 5)
        log.debug('in command mode')

        self.driver_client.cmd_dvr('start_direct')
        self.assert_state_change(PARProtocolState.DIRECT_ACCESS, 5)
        log.debug('in direct access')

        time.sleep(3)

        self.driver_client.cmd_dvr('stop_direct')
        self.assert_state_change(PARProtocolState.COMMAND, 5)
        log.debug('leaving direct access')

    def test_errors(self):
        """
        Verify response to erroneous commands and setting bad parameters.
        """
        self.assert_initialize_driver(PARProtocolState.COMMAND)

        #Assert an invalid command
        self.assert_driver_command_exception('ima_bad_command', exception_class=InstrumentCommandException)

        # Assert for a known command, invalid state.
        self.assert_driver_command_exception(PARProtocolEvent.STOP_AUTOSAMPLE,
                                             exception_class=InstrumentCommandException)

        # Assert set fails with a bad parameter (not ALL or a list).
        self.assert_set_exception('I am a bogus param.', exception_class=InstrumentParameterException)

        # #Assert set fails with bad parameter and bad value
        self.assert_set_exception('I am a bogus param.', value='bogus value',
                                  exception_class=InstrumentParameterException)

        # put driver in disconnected state.
        self.driver_client.cmd_dvr('disconnect')

        # Assert for a known command, invalid state.
        self.assert_driver_command_exception(PARProtocolEvent.STOP_AUTOSAMPLE,
                                             exception_class=InstrumentCommandException)

        # Test that the driver is in state disconnected.
        self.assert_state_change(DriverConnectionState.DISCONNECTED, timeout=TIMEOUT)

        # Setup the protocol state machine and the connection to port agent.
        self.driver_client.cmd_dvr('initialize')

        # Test that the driver is in state unconfigured.
        self.assert_state_change(DriverConnectionState.UNCONFIGURED, timeout=TIMEOUT)

        # Assert we forgot the comms parameter.
        self.assert_driver_command_exception('configure', exception_class=InstrumentParameterException)

        # Configure driver and transition to disconnected.
        self.driver_client.cmd_dvr('configure', self.port_agent_comm_config())

        # Test that the driver is in state disconnected.
        self.assert_state_change(DriverConnectionState.DISCONNECTED, timeout=TIMEOUT)

    def test_scheduled_status_command(self):
        """
        Verify the device status command can be triggered and run in command
        """
        self.assert_initialize_driver()
        self.assert_set(EngineeringParameter.ACQUIRE_STATUS_INTERVAL, "00:00:20")

        # Verify that the event got scheduled
        self.assert_async_particle_generation(DataParticleType.CONFIG, self.assert_config_parameters, timeout=60)

        # Reset the interval
        self.assert_set(EngineeringParameter.ACQUIRE_STATUS_INTERVAL, "00:00:10")

        # Verify that the event got scheduled
        self.assert_async_particle_generation(DataParticleType.CONFIG, self.assert_config_parameters, timeout=30)

        # This should unschedule the acquire status event
        self.assert_set(EngineeringParameter.ACQUIRE_STATUS_INTERVAL, "00:00:00")

        # Now verify that no more status particles get generated, provide generous timeout
        with self.assertRaises(AssertionError):
            self.assert_async_particle_generation(DataParticleType.CONFIG, self.assert_config_parameters, timeout=50)

        self.assert_current_state(PARProtocolState.COMMAND)

    def test_scheduled_status_autosample(self):
        """
        Verify the device status command can be triggered and run in autosample
        """
        self.assert_initialize_driver()
        self.assert_set(EngineeringParameter.ACQUIRE_STATUS_INTERVAL, "00:00:15")

        self.assert_driver_command(PARProtocolEvent.START_AUTOSAMPLE, state=PARProtocolState.AUTOSAMPLE, delay=1)
        self.assert_current_state(PARProtocolState.AUTOSAMPLE)

        #verify that the event got scheduled
        self.assert_async_particle_generation(DataParticleType.CONFIG, self.assert_config_parameters,
                                              particle_count=5, timeout=90)

        self.assert_driver_command(PARProtocolEvent.STOP_AUTOSAMPLE)


###############################################################################
#                            QUALIFICATION TESTS                              #
# Device specific qualification tests are for                                 #
# testing device specific capabilities                                        #
###############################################################################

@attr('QUAL', group='mi')
class SatlanticParProtocolQualificationTest(InstrumentDriverQualificationTestCase, PARMixin):
    """Qualification Test Container"""

    # Qualification tests live in the base class.  This class is extended
    # here so that when running this test from 'nosetests' all tests
    # (UNIT, INT, and QUAL) are run.

    def test_direct_access_telnet_mode(self):
        """
        @brief This test verifies that the Instrument Driver
               properly supports direct access to the physical
               instrument. (telnet mode)
        """
        ###
        # First test direct access and exit with a go command
        # call.  Also add a parameter change to verify DA
        # parameters are restored on DA exit.
        ###
        self.assert_enter_command_mode()
        self.assert_get_parameter(Parameter.MAXRATE, 4)

        # go into direct access, and muck up a setting.
        self.assert_direct_access_start_telnet()
        self.tcp_client.send_data("set maxrate 1" + EOLN)

        #need to sleep as the instrument needs time to apply the new param value
        time.sleep(5)

        # Verify the param value got changed on the instrument
        self.tcp_client.send_data("show maxrate" + EOLN)

        self.tcp_client.expect("Maximum Frame Rate: 1 Hz")
        self.assert_direct_access_stop_telnet()

        # verify the setting remained unchanged in the param dict
        self.assert_enter_command_mode()
        self.assert_get_parameter(Parameter.MAXRATE, 4)

    def test_direct_access_telnet_mode_autosample(self):
        """
        @brief Same as the previous DA test except in this test
               we force the instrument into streaming when in
               DA.  Then we need to verify the transition back
               to the driver works as expected.
        """
        self.assert_enter_command_mode()
        self.assert_get_parameter(Parameter.MAXRATE, 4)
        # go into direct access
        self.assert_direct_access_start_telnet()
        self.assertTrue(self.tcp_client)

        #start sampling
        self.tcp_client.send_data("exit!" + EOLN)
        time.sleep(2)

        #verify we're sampling
        self.tcp_client.expect("SATPAR")

        #Assert if stopping DA while autosampling, discover will put driver into Autosample state
        self.assert_direct_access_stop_telnet()
        self.assert_state_change(ResourceAgentState.STREAMING, PARProtocolState.AUTOSAMPLE, timeout=10)

        #now stop autosampling
        self.assert_stop_autosample()

    def test_direct_access_telnet_timeout(self):
        """
        Verify that direct access times out as expected and the agent transitions back to command mode.
        """
        self.assert_enter_command_mode()

        # go into direct access
        self.assert_direct_access_start_telnet(timeout=30)
        self.assertTrue(self.tcp_client)

        self.assert_state_change(ResourceAgentState.COMMAND, PARProtocolState.COMMAND, 180)

    def test_direct_access_telnet_closed(self):
        """
        Verify that a disconnection from the DA server transitions the agent back to
        command mode.
        """
        self.assert_enter_command_mode()

        # go into direct access
        self.assert_direct_access_start_telnet(timeout=600)
        self.assertTrue(self.tcp_client)
        self.tcp_client.disconnect()

        self.assert_state_change(ResourceAgentState.COMMAND, PARProtocolState.COMMAND, 120)

    def test_get_set_parameters(self):
        """
        Verify that parameters can be get/set properly
        """
        self.assert_enter_command_mode()

        #read/write params
        self.assert_set_parameter(Parameter.MAXRATE, 2)

        #read-only params
        self.assert_get_parameter(Parameter.FIRMWARE, "1.0.0")
        self.assert_get_parameter(Parameter.SERIAL, "4278190306")
        self.assert_get_parameter(Parameter.INSTRUMENT, "SATPAR")

    def test_poll(self):
        """
        Verify data particles for a single sample that are specific to PARAD
        """
        self.assert_enter_command_mode()
        self.assert_particle_polled(DriverEvent.ACQUIRE_SAMPLE, self.assert_particle_sample, DataParticleType.PARSED,
                                    timeout=60, sample_count=1)

    def test_autosample(self):
        """
        Verify data particles for auto-sampling that are specific to PARAD
        """
        self.assert_enter_command_mode()
        self.assert_start_autosample()

        # Default maxrate is 4, expecting a sample every 0.25 seconds. Note: Qual seems to have a 2 second lag.
        self.assert_particle_async(DataParticleType.PARSED, self.assert_particle_sample, particle_count=40, timeout=12)

        self.assert_stop_autosample()

    def test_acquire_status(self):
        """
        Verify the driver can command an acquire status from the instrument
        """
        self.assert_enter_command_mode()

        self.assert_particle_polled(PARCapability.ACQUIRE_STATUS, self.assert_config_parameters,
                                    DataParticleType.CONFIG)

        state = self.instrument_agent_client.get_agent_state()
        self.assertEqual(state, ResourceAgentState.COMMAND)

    def test_get_capabilities(self):
        """
        @brief Verify that the correct capabilities are returned from get_capabilities
        at various driver/agent states.
        """
        self.assert_enter_command_mode()

        ##################
        #  Command Mode
        ##################

        capabilities = {AgentCapabilityType.AGENT_COMMAND: self._common_agent_commands(ResourceAgentState.COMMAND),
                        AgentCapabilityType.AGENT_PARAMETER: self._common_agent_parameters(),
                        AgentCapabilityType.RESOURCE_COMMAND: [PARProtocolEvent.ACQUIRE_SAMPLE,
                                                               PARProtocolEvent.ACQUIRE_STATUS,
                                                               PARProtocolEvent.START_AUTOSAMPLE],
                        AgentCapabilityType.RESOURCE_INTERFACE: None,
                        AgentCapabilityType.RESOURCE_PARAMETER: list(self._driver_parameters.keys())}

        self.assert_enter_command_mode()
        self.assert_capabilities(capabilities)

        ##################
        #  Streaming Mode
        ##################
        capabilities = {AgentCapabilityType.AGENT_COMMAND: self._common_agent_commands(ResourceAgentState.STREAMING),
                        AgentCapabilityType.RESOURCE_COMMAND: [PARProtocolEvent.STOP_AUTOSAMPLE,
                                                               PARProtocolEvent.ACQUIRE_STATUS, ],
                        AgentCapabilityType.RESOURCE_PARAMETER: list(self._driver_parameters.keys())}

        self.assert_start_autosample()
        self.assert_capabilities(capabilities)
        self.assert_stop_autosample()

        # ##################
        # #  DA Mode
        # ##################
        capabilities[AgentCapabilityType.AGENT_COMMAND] = self._common_agent_commands(ResourceAgentState.DIRECT_ACCESS)
        capabilities[AgentCapabilityType.RESOURCE_COMMAND] = []

        self.assert_direct_access_start_telnet()
        self.assert_capabilities(capabilities)
        self.assert_direct_access_stop_telnet()

        #######################
        #  Uninitialized Mode
        #######################
        capabilities[AgentCapabilityType.AGENT_COMMAND] = self._common_agent_commands(ResourceAgentState.UNINITIALIZED)
        capabilities[AgentCapabilityType.RESOURCE_COMMAND] = []
        capabilities[AgentCapabilityType.RESOURCE_INTERFACE] = []
        capabilities[AgentCapabilityType.RESOURCE_PARAMETER] = []

        self.assert_reset()
        self.assert_capabilities(capabilities)