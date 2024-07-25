#!/usr/bin/env python

"""
@package mi.core.test.test_persistent_store
@file <git-workspace>/ooi/edex/com.raytheon.uf.ooi.plugin.instrumentagent/utility/edex_static/base/ooi/instruments/mi-instrument/mi/core/test/test_persistent_store.py
@author Johnathon Rusk
@brief Unit tests for PersistentStoreDict module
"""

# Note: Execute via, "nosetests -a UNIT -v mi/core/test/test_persistent_store.py"

__author__ = 'Johnathon Rusk'
__license__ = 'Apache 2.0'

from nose.plugins.attrib import attr
from mi.core.unit_test import MiUnitTest
import sys

from mi.core.persistent_store import PersistentStoreDict

@attr('UNIT', group='mi')
class TestPersistentStoreDict(MiUnitTest):
    def setUp(self):
        self.UNICODE_KEY = "UNICODE_KEY" # Test 'str' type key
        self.UNICODE_VALUES = ["this is a unicode string", "this is another unicode string"]
        self.INT_KEY = "INT_KEY"
        self.INT_VALUES = [1234, 5678]
        self.LONG_KEY = "LONG_KEY" # Test 'str' type key
        self.LONG_VALUES = [sys.maxsize + 1, sys.maxsize + 2]
        self.FLOAT_KEY = "FLOAT_KEY"
        self.FLOAT_VALUES = [56.78, 12.34]
        self.BOOL_KEY = "BOOL_KEY" # Test 'str' type key
        self.BOOL_VALUES = [True, False]
        self.DICT_KEY = "DICT_KEY"
        self.DICT_VALUES = [{"KEY_1":1, "KEY_2":2, "KEY_3":3}, {"KEY_4":4, "KEY_5":5, "KEY_6":6}]
        self.LIST_KEY = "LIST_KEY" # Test 'str' type key
        self.LIST_VALUES = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 0]]
        self.persistentStoreDict = PersistentStoreDict("unit_test", "GI01SUMO-00001")

    def tearDown(self):
        self.persistentStoreDict.clear() # NOTE: This technically assumes the delete functionality works.

    def helper_get(self, key, expectedValue, expectedValueType):
        self.assertIn(type(key), [str, str])
        value = self.persistentStoreDict[key]
        self.assertIs(type(value), expectedValueType)
        self.assertEqual(value, expectedValue)

    def helper_set(self, key, value, valueType, shouldAddKey):
        self.assertIn(type(key), [str, str])
        self.assertIs(type(value), valueType)
        self.assertIs(type(shouldAddKey), bool)
        initialKeyCount = len(list(self.persistentStoreDict.keys()))
        self.persistentStoreDict[key] = value
        self.assertEqual(len(list(self.persistentStoreDict.keys())), (initialKeyCount + 1) if shouldAddKey else initialKeyCount)

    def helper_del(self, key):
        self.assertIn(type(key), [str, str])
        initialKeyCount = len(list(self.persistentStoreDict.keys()))
        del self.persistentStoreDict[key]
        self.assertEqual(len(list(self.persistentStoreDict.keys())), initialKeyCount - 1)

    def test_createRecords_success_unicode(self):
        self.helper_set(self.UNICODE_KEY, self.UNICODE_VALUES[0], str, True)

    def test_createRecords_success_int(self):
        self.helper_set(self.INT_KEY, self.INT_VALUES[0], int, True)

    def test_createRecords_success_long(self):
        self.helper_set(self.LONG_KEY, self.LONG_VALUES[0], int, True)

    def test_createRecords_success_float(self):
        self.helper_set(self.FLOAT_KEY, self.FLOAT_VALUES[0], float, True)

    def test_createRecords_success_bool(self):
        self.helper_set(self.BOOL_KEY, self.BOOL_VALUES[0], bool, True)

    def test_createRecords_success_dict(self):
        self.helper_set(self.DICT_KEY, self.DICT_VALUES[0], dict, True)

    def test_createRecords_success_list(self):
        self.helper_set(self.LIST_KEY, self.LIST_VALUES[0], list, True)

    def test_createRecords_fail_badKeyType(self):
        key = 0
        value = "this will fail"
        self.assertNotIn(type(key), [str, str])
        self.assertIn(type(value), [str, int, int, float, bool, dict, list])
        with self.assertRaises(TypeError) as contextManager:
            self.persistentStoreDict[key] = value
        self.assertEqual(contextManager.exception.args[0], "Key must be of type 'str' or 'unicode'.")

    def test_createRecords_fail_badItemType(self):
        key = "this will fail"
        value = 2+3j
        self.assertIn(type(key), [str, str])
        self.assertNotIn(type(value), [str, int, int, float, bool, dict, list])
        with self.assertRaises(TypeError) as contextManager:
            self.persistentStoreDict[key] = value
        self.assertEqual(contextManager.exception.args[0], "Value must be of type: 'unicode', 'int', 'long', 'float', 'bool', 'dict', or 'list'")

    def test_createRecords_fail_badItemType_nested(self):
        key = "this will fail"
        value = {"KEY_1":[1, 2, 3], "KEY_2":[1+2j, 3+4j, 5+6j]}
        self.assertIn(type(key), [str, str])
        self.assertIn(type(value), [str, int, int, float, bool, dict, list])
        self.assertNotIn(type(value['KEY_2'][0]), [str, int, int, float, bool, dict, list])
        with self.assertRaises(TypeError) as contextManager:
            self.persistentStoreDict[key] = value
        self.assertEqual(contextManager.exception.args[0], "Value must be of type: 'unicode', 'int', 'long', 'float', 'bool', 'dict', or 'list'")

    def test_getRecords_success_unicode(self):
        self.helper_set(self.UNICODE_KEY, self.UNICODE_VALUES[0], str, True)
        self.helper_get(self.UNICODE_KEY, self.UNICODE_VALUES[0], str)

    def test_getRecords_success_int(self):
        self.helper_set(self.INT_KEY, self.INT_VALUES[0], int, True)
        self.helper_get(self.INT_KEY, self.INT_VALUES[0], int)

    def test_getRecords_success_long(self):
        self.helper_set(self.LONG_KEY, self.LONG_VALUES[0], int, True)
        self.helper_get(self.LONG_KEY, self.LONG_VALUES[0], int)

    def test_getRecords_success_float(self):
        self.helper_set(self.FLOAT_KEY, self.FLOAT_VALUES[0], float, True)
        self.helper_get(self.FLOAT_KEY, self.FLOAT_VALUES[0], float)

    def test_getRecords_success_bool(self):
        self.helper_set(self.BOOL_KEY, self.BOOL_VALUES[0], bool, True)
        self.helper_get(self.BOOL_KEY, self.BOOL_VALUES[0], bool)

    def test_getRecords_success_dict(self):
        self.helper_set(self.DICT_KEY, self.DICT_VALUES[0], dict, True)
        self.helper_get(self.DICT_KEY, self.DICT_VALUES[0], dict)

    def test_getRecords_success_list(self):
        self.helper_set(self.LIST_KEY, self.LIST_VALUES[0], list, True)
        self.helper_get(self.LIST_KEY, self.LIST_VALUES[0], list)

    def test_getRecords_fail_badKeyType(self):
        key = 0
        self.assertNotIn(type(key), [str, str])
        with self.assertRaises(TypeError) as contextManager:
            value = self.persistentStoreDict[key]
        self.assertEqual(contextManager.exception.args[0], "Key must be of type 'str' or 'unicode'.")

    def test_getRecords_fail_keyNotFound(self):
        key = "this will fail"
        self.assertIn(type(key), [str, str])
        with self.assertRaises(KeyError) as contextManager:
            value = self.persistentStoreDict[key]
        self.assertEqual(contextManager.exception.args[0], "No item found with key: '{0}'".format(key))

    def test_updateRecords_success_unicode(self):
        self.helper_set(self.UNICODE_KEY, self.UNICODE_VALUES[0], str, True)
        self.helper_get(self.UNICODE_KEY, self.UNICODE_VALUES[0], str)
        self.helper_set(self.UNICODE_KEY, self.UNICODE_VALUES[1], str, False)
        self.helper_get(self.UNICODE_KEY, self.UNICODE_VALUES[1], str)

    def test_updateRecords_success_int(self):
        self.helper_set(self.INT_KEY, self.INT_VALUES[0], int, True)
        self.helper_get(self.INT_KEY, self.INT_VALUES[0], int)
        self.helper_set(self.INT_KEY, self.INT_VALUES[1], int, False)
        self.helper_get(self.INT_KEY, self.INT_VALUES[1], int)

    def test_updateRecords_success_long(self):
        self.helper_set(self.LONG_KEY, self.LONG_VALUES[0], int, True)
        self.helper_get(self.LONG_KEY, self.LONG_VALUES[0], int)
        self.helper_set(self.LONG_KEY, self.LONG_VALUES[1], int, False)
        self.helper_get(self.LONG_KEY, self.LONG_VALUES[1], int)

    def test_updateRecords_success_float(self):
        self.helper_set(self.FLOAT_KEY, self.FLOAT_VALUES[0], float, True)
        self.helper_get(self.FLOAT_KEY, self.FLOAT_VALUES[0], float)
        self.helper_set(self.FLOAT_KEY, self.FLOAT_VALUES[1], float, False)
        self.helper_get(self.FLOAT_KEY, self.FLOAT_VALUES[1], float)

    def test_updateRecords_success_bool(self):
        self.helper_set(self.BOOL_KEY, self.BOOL_VALUES[0], bool, True)
        self.helper_get(self.BOOL_KEY, self.BOOL_VALUES[0], bool)
        self.helper_set(self.BOOL_KEY, self.BOOL_VALUES[1], bool, False)
        self.helper_get(self.BOOL_KEY, self.BOOL_VALUES[1], bool)

    def test_updateRecords_success_dict(self):
        self.helper_set(self.DICT_KEY, self.DICT_VALUES[0], dict, True)
        self.helper_get(self.DICT_KEY, self.DICT_VALUES[0], dict)
        self.helper_set(self.DICT_KEY, self.DICT_VALUES[1], dict, False)
        self.helper_get(self.DICT_KEY, self.DICT_VALUES[1], dict)

    def test_updateRecords_success_list(self):
        self.helper_set(self.LIST_KEY, self.LIST_VALUES[0], list, True)
        self.helper_get(self.LIST_KEY, self.LIST_VALUES[0], list)
        self.helper_set(self.LIST_KEY, self.LIST_VALUES[1], list, False)
        self.helper_get(self.LIST_KEY, self.LIST_VALUES[1], list)

    def test_removeRecords_success_unicode(self):
        self.helper_set(self.UNICODE_KEY, self.UNICODE_VALUES[0], str, True)
        self.helper_del(self.UNICODE_KEY)

    def test_removeRecords_success_int(self):
        self.helper_set(self.INT_KEY, self.INT_VALUES[0], int, True)
        self.helper_del(self.INT_KEY)

    def test_removeRecords_success_long(self):
        self.helper_set(self.LONG_KEY, self.LONG_VALUES[0], int, True)
        self.helper_del(self.LONG_KEY)

    def test_removeRecords_success_float(self):
        self.helper_set(self.FLOAT_KEY, self.FLOAT_VALUES[0], float, True)
        self.helper_del(self.FLOAT_KEY)

    def test_removeRecords_success_bool(self):
        self.helper_set(self.BOOL_KEY, self.BOOL_VALUES[0], bool, True)
        self.helper_del(self.BOOL_KEY)

    def test_removeRecords_success_dict(self):
        self.helper_set(self.DICT_KEY, self.DICT_VALUES[0], dict, True)
        self.helper_del(self.DICT_KEY)

    def test_removeRecords_success_list(self):
        self.helper_set(self.LIST_KEY, self.LIST_VALUES[0], list, True)
        self.helper_del(self.LIST_KEY)

    def test_removeRecords_fail_badKeyType(self):
        key = 0
        self.assertNotIn(type(key), [str, str])
        with self.assertRaises(TypeError) as contextManager:
            del self.persistentStoreDict[key]
        self.assertEqual(contextManager.exception.args[0], "Key must be of type 'str' or 'unicode'.")

    def test_removeRecords_fail_keyNotFound(self):
        key = "this will fail"
        self.assertIn(type(key), [str, str])
        with self.assertRaises(KeyError) as contextManager:
            del self.persistentStoreDict[key]
        self.assertEqual(contextManager.exception.args[0], "No item found with key: '{0}'".format(key))

