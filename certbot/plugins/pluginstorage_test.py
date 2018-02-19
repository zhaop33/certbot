"""Tests for certbot.plugins.common.PluginStorage"""
import json
import mock
import os
import shutil
import tempfile
import unittest

from certbot import errors

from certbot.plugins import common


class PluginStorageTest(unittest.TestCase):
    """Test for certbot.plugins.common.PluginStorage"""

    def setUp(self):

        class MockPlugin(common.Installer):
            """Mock plugin"""
            pass
        self.plugin_cls = MockPlugin
        self.config_dir = tempfile.mkdtemp()
        self.config = mock.MagicMock(config_dir=self.config_dir)
        with mock.patch("certbot.reverter.util"):
            self.plugin = MockPlugin(config=self.config, name="mockplugin")

    def tearDown(self):
        shutil.rmtree(self.config_dir)

    def test_initialize_no_configdir(self):
        delattr(self.plugin.config, "config_dir")
        self.plugin.storage.initialize_storage()
        self.assertTrue(self.plugin.storage.storagepath == None)

    def test_load_errors(self):
        with open(os.path.join(self.config_dir, ".pluginstorage.json"), "w") as fh:
            fh.write("dummy")

        # When unable to read file that exists
        mock_open = mock.mock_open()
        mock_open.side_effect = IOError
        self.plugin.storage.storagepath = os.path.join(self.config_dir,
                                                       ".pluginstorage.json")
        with mock.patch("six.moves.builtins.open", mock_open):
            with mock.patch('os.path.isfile', return_value=True):
                with mock.patch("certbot.reverter.util"):
                    self.assertRaises(errors.PluginStorageError,
                                    self.plugin.storage.load)

        # When pluginstorage path is None
        mock_open.side_effect = TypeError
        with mock.patch("six.moves.builtins.open", mock_open):
            with mock.patch("certbot.reverter.util"):
                nostoragepath = self.plugin_cls(self.config, "mockplugin")
                self.assertRaises(errors.PluginStorageError,
                                nostoragepath.storage.load)

        # When file exists but is completely empty
        with open(os.path.join(self.config_dir, ".pluginstorage.json"), "w") as fh:
            fh.write('')
        with mock.patch("certbot.plugins.common.logger.debug") as mock_log:
            # Should not error out but write a debug log line instead
            with mock.patch("certbot.reverter.util"):
                nocontent = self.plugin_cls(self.config, "mockplugin")
            nocontent.storage.fetch("value")
            self.assertTrue(mock_log.called)
            self.assertTrue("no values loaded" in mock_log.call_args[0][0])

        # File is corrupted
        with open(os.path.join(self.config_dir, ".pluginstorage.json"), "w") as fh:
            fh.write('invalid json')
        with mock.patch("certbot.plugins.common.logger.error") as mock_log:
            with mock.patch("certbot.reverter.util"):
                corrupted = self.plugin_cls(self.config, "mockplugin")
            self.assertRaises(errors.PluginError,
                              corrupted.storage.fetch,
                              "value")
            self.assertTrue("is corrupted" in mock_log.call_args[0][0])

    def test_save_no_storagepath(self):
        with mock.patch("certbot.plugins.common.logger.error") as mock_log:
            self.assertRaises(errors.PluginStorageError,
                              self.plugin.storage.save)
            self.assertTrue("Unable to save" in mock_log.call_args[0][0])

    def test_save_errors(self):
        with mock.patch("certbot.plugins.common.logger.error") as mock_log:
            # Set data as something that can't be serialized
            self.plugin.storage.initialized = True
            self.plugin.storage.storagepath = "/tmp/whatever"
            self.plugin.storage._data = self.plugin_cls  # pylint: disable=protected-access
            self.assertRaises(errors.PluginStorageError,
                              self.plugin.storage.save)
            self.assertTrue("Could not serialize" in mock_log.call_args[0][0])

        # When unable to write to file
        mock_open = mock.mock_open()
        mock_open.side_effect = IOError
        with mock.patch("os.open", mock_open):
            with mock.patch("certbot.plugins.common.logger.error") as mock_log:
                self.plugin.storage._data = {"valid": "data"}  # pylint: disable=protected-access
                self.assertRaises(errors.PluginStorageError,
                                  self.plugin.storage.save)
                self.assertTrue("Could not write" in mock_log.call_args[0][0])

    def test_namespace_isolation(self):
        with mock.patch("certbot.reverter.util"):
            plugin1 = self.plugin_cls(self.config, "first")
            plugin2 = self.plugin_cls(self.config, "second")
        plugin1.storage.put("first_key", "first_value")
        self.assertEqual(plugin2.storage.fetch("first_key"), None)
        self.assertEqual(plugin2.storage.fetch("first"), None)
        self.assertEqual(plugin1.storage.fetch("first_key"), "first_value")


    def test_saved_state(self):
        self.plugin.storage.put("testkey", "testvalue")
        # Write to disk
        self.plugin.storage.save()
        with mock.patch("certbot.reverter.util"):
            another = self.plugin_cls(self.config, "mockplugin")
        self.assertEqual(another.storage.fetch("testkey"), "testvalue")

        with open(os.path.join(self.config.config_dir,
                               ".pluginstorage.json"), 'r') as fh:
            psdata = fh.read()
        psjson = json.loads(psdata)
        self.assertTrue("mockplugin" in psjson.keys())
        self.assertEqual(len(psjson), 1)
        self.assertEqual(psjson["mockplugin"]["testkey"], "testvalue")







if __name__ == "__main__":
    unittest.main()  # pragma: no cover
