# coding: utf-8
#
# Copyright 2019 The Oppia Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for scripts/deploy.py."""

from __future__ import absolute_import  # pylint: disable=import-only-modules
from __future__ import unicode_literals  # pylint: disable=import-only-modules

import os
import shutil
import subprocess
import sys
import tempfile

from core.tests import test_utils

import python_utils

from . import common
from . import deploy
from . import gcloud_adapter
from . import install_third_party_libs
from . import update_configs

_PARENT_DIR = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
_PY_GITHUB_PATH = os.path.join(_PARENT_DIR, 'oppia_tools', 'PyGithub-1.43.7')
sys.path.insert(0, _PY_GITHUB_PATH)

# pylint: disable=wrong-import-position
import github # isort:skip
# pylint: enable=wrong-import-position

RELEASE_TEST_DIR = os.path.join('core', 'tests', 'release_sources', '')

MOCK_FECONF_FILEPATH = os.path.join(RELEASE_TEST_DIR, 'feconf.txt')
INVALID_CONSTANTS_WITH_WRONG_DEV_MODE = os.path.join(
    RELEASE_TEST_DIR, 'invalid_constants_with_wrong_dev_mode.txt')
INVALID_CONSTANTS_WITH_WRONG_BUCKET_NAME = os.path.join(
    RELEASE_TEST_DIR, 'invalid_constants_with_wrong_bucket_name.txt')
VALID_CONSTANTS = os.path.join(RELEASE_TEST_DIR, 'valid_constants.txt')


class MockCD(python_utils.OBJECT):
    """Mock for context manager for changing the current working directory."""
    def __init__(self, unused_new_path):
        pass

    def __enter__(self):
        pass

    def __exit__(self, unused_arg1, unused_arg2, unused_arg3):
        pass


class DeployTests(test_utils.GenericTestBase):
    """Test the methods for deploying release."""
    def setUp(self):
        super(DeployTests, self).setUp()
        # pylint: disable=unused-argument
        def mock_main(args):
            pass
        def mock_copytree(unused_dir1, unused_dir2, ignore):
            pass
        # pylint: enable=unused-argument
        def mock_copyfile(unused_file1, unused_file2):
            pass
        def mock_get_branch():
            return 'release-1.2.3'
        def mock_check():
            pass
        def mock_exists(unused_path):
            return True
        def mock_check_output(unused_cmd_tokens):
            return 'output'
        def mock_listdir(unused_dir):
            return ['dir1', 'dir2']
        def mock_open_tab(unused_url):
            pass
        def mock_get_currently_served_version(unused_app_name):
            return '1.2.3'
        def mock_input():
            return 'y'
        def mock_run_cmd(unused_cmd_tokens):
            pass

        self.install_swap = self.swap(
            install_third_party_libs, 'main', mock_main)
        self.copytree_swap = self.swap(shutil, 'copytree', mock_copytree)
        self.copyfile_swap = self.swap(shutil, 'copyfile', mock_copyfile)
        self.get_branch_swap = self.swap(
            common, 'get_current_branch_name', mock_get_branch)
        self.args_swap = self.swap(
            sys, 'argv', ['deploy.py', '--app_name=oppiatestserver'])
        self.cwd_check_swap = self.swap(
            common, 'require_cwd_to_be_oppia', mock_check)
        self.release_script_exist_swap = self.swap(
            common, 'ensure_release_scripts_folder_exists_and_is_up_to_date',
            mock_check)
        self.gcloud_available_swap = self.swap(
            gcloud_adapter, 'require_gcloud_to_be_available', mock_check)
        self.dir_exists_swap = self.swap(
            common, 'ensure_directory_exists', mock_exists)
        self.exists_swap = self.swap(os.path, 'exists', mock_exists)
        self.check_output_swap = self.swap(
            subprocess, 'check_output', mock_check_output)
        self.cd_swap = self.swap(common, 'CD', MockCD)
        self.listdir_swap = self.swap(os, 'listdir', mock_listdir)
        self.open_tab_swap = self.swap(
            common, 'open_new_tab_in_browser_if_possible', mock_open_tab)
        self.get_version_swap = self.swap(
            gcloud_adapter, 'get_currently_served_version',
            mock_get_currently_served_version)
        self.input_swap = self.swap(python_utils, 'INPUT', mock_input)
        self.run_swap = self.swap(common, 'run_cmd', mock_run_cmd)

    def test_invalid_app_name(self):
        args_swap = self.swap(
            sys, 'argv', ['deploy.py', '--app_name=invalid'])
        with args_swap, self.assertRaisesRegexp(
            Exception, 'Invalid app name: invalid'):
            deploy.execute_deployment()

    def test_missing_app_name(self):
        args_swap = self.swap(
            sys, 'argv', ['deploy.py'])
        with args_swap, self.assertRaisesRegexp(
            Exception, 'No app name specified.'):
            deploy.execute_deployment()

    def test_invalid_version(self):
        args_swap = self.swap(
            sys, 'argv', [
                'deploy.py', '--app_name=oppiaserver', '--version=1.2.3'])
        with args_swap, self.assertRaisesRegexp(
            Exception, 'Cannot use custom version with production app.'):
            deploy.execute_deployment()

    def test_invalid_branch(self):
        def mock_get_branch():
            return 'invalid'
        get_branch_swap = self.swap(
            common, 'get_current_branch_name', mock_get_branch)
        with get_branch_swap, self.args_swap, self.install_swap:
            with self.assertRaisesRegexp(
                Exception,
                'The deployment script must be run from a release branch.'):
                deploy.execute_deployment()

    def test_invalid_release_version(self):
        hyphen_swap = self.swap(deploy, 'HYPHEN_CHAR', '.')
        with self.get_branch_swap, self.args_swap, self.install_swap:
            with hyphen_swap, self.assertRaisesRegexp(
                Exception,
                'Current release version has \'.\' character.'):
                deploy.execute_deployment()

    def test_invalid_last_commit_msg(self):
        args_swap = self.swap(
            sys, 'argv', ['deploy.py', '--app_name=oppiaserver'])
        def mock_check_output(unused_cmd_tokens):
            return 'Invalid'
        out_swap = self.swap(
            subprocess, 'check_output', mock_check_output)
        with self.get_branch_swap, self.install_swap, self.cwd_check_swap:
            with self.release_script_exist_swap, self.gcloud_available_swap:
                with self.run_swap, args_swap, out_swap:
                    with self.assertRaisesRegexp(
                        Exception, 'Invalid last commit message: Invalid.'):
                        deploy.execute_deployment()

    def test_missing_mailgun_api(self):
        args_swap = self.swap(
            sys, 'argv', ['deploy.py', '--app_name=oppiaserver'])
        feconf_swap = self.swap(
            deploy, 'FECONF_PATH', MOCK_FECONF_FILEPATH)
        def mock_main():
            pass
        def mock_get_personal_access_token():
            return 'test'
        def mock_get_organization(unused_self, unused_name):
            return github.Organization.Organization(
                requester='', headers='', attributes={}, completed='')
        def mock_get_repo(unused_self, unused_org):
            return 'repo'
        def mock_check_blocking_bug_issue_count(unused_repo):
            pass
        def mock_check_prs_for_current_release_are_released(unused_repo):
            pass
        def mock_check_output(unused_cmd_tokens):
            return 'Update authors and changelog for v1.2.3'
        config_swap = self.swap(update_configs, 'main', mock_main)
        get_token_swap = self.swap(
            common, 'get_personal_access_token', mock_get_personal_access_token)
        get_org_swap = self.swap(
            github.Github, 'get_organization', mock_get_organization)
        get_repo_swap = self.swap(
            github.Organization.Organization, 'get_repo', mock_get_repo)
        bug_check_swap = self.swap(
            common, 'check_blocking_bug_issue_count',
            mock_check_blocking_bug_issue_count)
        pr_check_swap = self.swap(
            common, 'check_prs_for_current_release_are_released',
            mock_check_prs_for_current_release_are_released)
        out_swap = self.swap(
            subprocess, 'check_output', mock_check_output)
        with self.get_branch_swap, self.install_swap, self.cwd_check_swap:
            with self.release_script_exist_swap, self.gcloud_available_swap:
                with self.run_swap, config_swap, get_token_swap, get_org_swap:
                    with get_repo_swap, bug_check_swap, pr_check_swap, out_swap:
                        with args_swap, feconf_swap, self.assertRaisesRegexp(
                            Exception,
                            'The mailgun API key must be added before '
                            'deployment.'):
                            deploy.execute_deployment()

    def test_missing_third_party_dir(self):
        third_party_swap = self.swap(deploy, 'THIRD_PARTY_DIR', 'INVALID_DIR')
        with self.get_branch_swap, self.install_swap, self.cwd_check_swap:
            with self.release_script_exist_swap, self.gcloud_available_swap:
                with self.run_swap, self.args_swap:
                    with third_party_swap, self.assertRaisesRegexp(
                        Exception,
                        'Could not find third_party directory at INVALID_DIR. '
                        'Please run install_third_party_libs.py prior to '
                        'running this script.'):
                        deploy.execute_deployment()

    def test_invalid_dir_access(self):
        def mock_getcwd():
            return 'invalid'
        getcwd_swap = self.swap(os, 'getcwd', mock_getcwd)
        with self.get_branch_swap, self.install_swap, self.cwd_check_swap:
            with self.release_script_exist_swap, self.gcloud_available_swap:
                with self.args_swap, self.exists_swap, self.check_output_swap:
                    with self.dir_exists_swap, self.copytree_swap, self.cd_swap:
                        with self.run_swap, getcwd_swap:
                            with self.assertRaisesRegexp(
                                Exception,
                                'Invalid directory accessed '
                                'during deployment: invalid'):
                                deploy.execute_deployment()

    def test_function_calls(self):
        check_function_calls = {
            'preprocess_release_gets_called': False,
            'update_and_check_indexes_gets_called': False,
            'build_scripts_gets_called': False,
            'deploy_application_and_write_log_entry_gets_called': False,
            'switch_version_gets_called': False,
            'flush_memcache_gets_called': False,
            'check_breakage_gets_called': False
        }
        expected_check_function_calls = {
            'preprocess_release_gets_called': True,
            'update_and_check_indexes_gets_called': True,
            'build_scripts_gets_called': True,
            'deploy_application_and_write_log_entry_gets_called': True,
            'switch_version_gets_called': True,
            'flush_memcache_gets_called': True,
            'check_breakage_gets_called': True
        }
        def mock_getcwd():
            return 'deploy-oppiatestserver-release-1.2.3-%s' % (
                deploy.CURRENT_DATETIME.strftime('%Y%m%d-%H%M%S'))
        def mock_preprocess_release(unused_app_name, unused_deploy_data_path):
            check_function_calls['preprocess_release_gets_called'] = True
        def mock_update_and_check_indexes(unused_app_name):
            check_function_calls['update_and_check_indexes_gets_called'] = True
        def mock_build_scripts():
            check_function_calls['build_scripts_gets_called'] = True
        def mock_deploy_application_and_write_log_entry(
                unused_app_name, unused_version_to_deploy_to,
                unused_current_git_revision):
            check_function_calls[
                'deploy_application_and_write_log_entry_gets_called'] = True
        def mock_switch_version(
                unused_app_name, unused_current_release_version):
            check_function_calls['switch_version_gets_called'] = True
        def mock_flush_memcache(unused_app_name):
            check_function_calls['flush_memcache_gets_called'] = True
        def mock_check_breakage(
                unused_app_name, unused_current_release_version):
            check_function_calls['check_breakage_gets_called'] = True

        cwd_swap = self.swap(os, 'getcwd', mock_getcwd)
        preprocess_swap = self.swap(
            deploy, 'preprocess_release', mock_preprocess_release)
        update_swap = self.swap(
            deploy, 'update_and_check_indexes', mock_update_and_check_indexes)
        build_swap = self.swap(deploy, 'build_scripts', mock_build_scripts)
        deploy_swap = self.swap(
            deploy, 'deploy_application_and_write_log_entry',
            mock_deploy_application_and_write_log_entry)
        switch_swap = self.swap(
            deploy, 'switch_version', mock_switch_version)
        memcache_swap = self.swap(
            deploy, 'flush_memcache', mock_flush_memcache)
        check_breakage_swap = self.swap(
            deploy, 'check_breakage', mock_check_breakage)

        with self.get_branch_swap, self.install_swap, self.cwd_check_swap:
            with self.release_script_exist_swap, self.gcloud_available_swap:
                with self.args_swap, self.exists_swap, self.check_output_swap:
                    with self.dir_exists_swap, self.copytree_swap, self.cd_swap:
                        with cwd_swap, preprocess_swap, update_swap, build_swap:
                            with deploy_swap, switch_swap, self.run_swap:
                                with memcache_swap, check_breakage_swap:
                                    deploy.execute_deployment()
        self.assertEqual(check_function_calls, expected_check_function_calls)

    def test_missing_deploy_data_dir(self):
        with self.assertRaisesRegexp(
            Exception, 'Could not find deploy_data directory at invalid_path'):
            deploy.preprocess_release('oppiaserver', 'invalid_path')

    def test_missing_deploy_files(self):
        def mock_exists(path):
            if path == 'deploy_dir':
                return True
            return False
        exists_swap = self.swap(os.path, 'exists', mock_exists)
        with exists_swap, self.assertRaisesRegexp(
            Exception,
            'Could not find source path deploy_dir/%s. Please '
            'check your deploy_data folder.' % deploy.FILES_AT_ROOT[0]):
            deploy.preprocess_release('oppiaserver', 'deploy_dir')

    def test_missing_assets_files(self):
        def mock_exists(path):
            if 'deploy_dir' in path:
                return True
            return False
        exists_swap = self.swap(os.path, 'exists', mock_exists)
        files_swap = self.swap(deploy, 'FILES_AT_ROOT', ['invalid.txt'])
        with exists_swap, files_swap, self.assertRaisesRegexp(
            Exception,
            'Could not find destination path %s. Has the code been '
            'updated in the meantime?' % os.path.join(
                os.getcwd(), 'assets', 'invalid.txt')):
            deploy.preprocess_release('oppiaserver', 'deploy_dir')

    def test_missing_images_dir(self):
        def mock_exists(path):
            if 'invalid' not in path:
                return True
            return False
        exists_swap = self.swap(os.path, 'exists', mock_exists)
        images_dir_swap = self.swap(deploy, 'IMAGE_DIRS', ['invalid'])

        with exists_swap, images_dir_swap, self.copyfile_swap:
            with self.assertRaisesRegexp(
                Exception,
                'Could not find source dir deploy_dir/images/invalid. '
                'Please check your deploy_data folder.'):
                deploy.preprocess_release('oppiaserver', 'deploy_dir')

    def test_invalid_dev_mode(self):
        constants_swap = self.swap(
            deploy, 'CONSTANTS_FILE_PATH',
            INVALID_CONSTANTS_WITH_WRONG_DEV_MODE)
        with self.exists_swap, self.copyfile_swap, constants_swap:
            with self.listdir_swap, self.assertRaises(AssertionError):
                deploy.preprocess_release('oppiaserver', 'deploy_dir')

    def test_invalid_bucket_name(self):
        constants_swap = self.swap(
            deploy, 'CONSTANTS_FILE_PATH',
            INVALID_CONSTANTS_WITH_WRONG_BUCKET_NAME)
        with self.exists_swap, self.copyfile_swap, constants_swap:
            with self.listdir_swap, self.assertRaises(AssertionError):
                deploy.preprocess_release('oppiaserver', 'deploy_dir')

    def test_constants_are_updated_correctly(self):
        constants_swap = self.swap(
            deploy, 'CONSTANTS_FILE_PATH', VALID_CONSTANTS)
        with python_utils.open_file(VALID_CONSTANTS, 'r') as f:
            original_content = f.read()
        expected_content = original_content.replace(
            '"DEV_MODE": true', '"DEV_MODE": false').replace(
                '"GCS_RESOURCE_BUCKET_NAME": "None-resources",',
                '"GCS_RESOURCE_BUCKET_NAME": "oppiaserver%s",' % (
                    deploy.BUCKET_NAME_SUFFIX))
        try:
            with self.exists_swap, self.copyfile_swap, constants_swap:
                with self.listdir_swap:
                    deploy.preprocess_release('oppiaserver', 'deploy_dir')
            with python_utils.open_file(VALID_CONSTANTS, 'r') as f:
                self.assertEqual(f.read(), expected_content)
        finally:
            with python_utils.open_file(VALID_CONSTANTS, 'w') as f:
                f.write(original_content)

    def test_indexes_not_serving(self):
        check_function_calls = {
            'update_indexes_gets_called': False,
            'check_all_indexes_are_serving_gets_called': False
        }
        expected_check_function_calls = {
            'update_indexes_gets_called': True,
            'check_all_indexes_are_serving_gets_called': True
        }
        def mock_update_indexes(unused_index_yaml_path, unused_app_name):
            check_function_calls['update_indexes_gets_called'] = True
        def mock_check_indexes(unused_app_name):
            check_function_calls[
                'check_all_indexes_are_serving_gets_called'] = True
            return False

        update_indexes_swap = self.swap(
            gcloud_adapter, 'update_indexes', mock_update_indexes)
        check_indexes_swap = self.swap(
            gcloud_adapter, 'check_all_indexes_are_serving', mock_check_indexes)
        with self.open_tab_swap, update_indexes_swap, check_indexes_swap:
            with self.assertRaisesRegexp(
                Exception,
                'Please wait for all indexes to serve, then run this '
                'script again to complete the deployment. For details, '
                'visit the indexes page. Exiting.'):
                deploy.update_and_check_indexes('oppiaserver')
        self.assertEqual(check_function_calls, expected_check_function_calls)

    def test_build(self):
        process = subprocess.Popen(['echo', 'test'], stdout=subprocess.PIPE)
        cmd_tokens = []
        # pylint: disable=unused-argument
        def mock_popen(tokens, stdout):
            cmd_tokens.extend(tokens)
            return process
        # pylint: enable=unused-argument
        with self.swap(subprocess, 'Popen', mock_popen):
            deploy.build_scripts()
        self.assertEqual(
            cmd_tokens, ['python', '-m', 'scripts.build', '--prod_env'])

    def test_build_failure(self):
        process = subprocess.Popen(['test'], stdout=subprocess.PIPE)
        process.return_code = 1
        cmd_tokens = []
        # pylint: disable=unused-argument
        def mock_popen(tokens, stdout):
            cmd_tokens.extend(tokens)
            return process
        # pylint: enable=unused-argument
        popen_swap = self.swap(subprocess, 'Popen', mock_popen)
        with popen_swap, self.assertRaisesRegexp(Exception, 'Build failed.'):
            deploy.build_scripts()
        self.assertEqual(
            cmd_tokens, ['python', '-m', 'scripts.build', '--prod_env'])

    def test_deploy_application(self):
        check_function_calls = {
            'deploy_application_gets_called': False
        }
        expected_check_function_calls = {
            'deploy_application_gets_called': True
        }
        # pylint: disable=unused-argument
        def mock_deploy(unused_yaml_path, unused_app_name, version='version'):
            check_function_calls['deploy_application_gets_called'] = True
        # pylint: enable=unused-argument
        deploy_swap = self.swap(
            gcloud_adapter, 'deploy_application', mock_deploy)
        temp_log_file = tempfile.NamedTemporaryFile().name
        log_swap = self.swap(deploy, 'LOG_FILE_PATH', temp_log_file)
        with deploy_swap, log_swap, self.dir_exists_swap:
            deploy.deploy_application_and_write_log_entry(
                'oppiaserver', '1.2.3', 'git-rev')
        self.assertEqual(check_function_calls, expected_check_function_calls)
        with python_utils.open_file(temp_log_file, 'r') as f:
            self.assertEqual(
                f.read(),
                'Successfully deployed to oppiaserver at '
                '%s (version git-rev)\n' % (
                    deploy.CURRENT_DATETIME.strftime('%Y-%m-%d %H:%M:%S'),
                ))

    def test_successful_flush_memcache(self):
        def mock_flush_memcache(unused_app_name):
            return True
        check_function_calls = {
            'open_tab_gets_called': False
        }
        expected_check_function_calls = {
            'open_tab_gets_called': False
        }
        def mock_open_tab(unused_url):
            check_function_calls['open_tab_gets_called'] = True
        flush_memcache_swap = self.swap(
            gcloud_adapter, 'flush_memcache', mock_flush_memcache)
        open_tab_swap = self.swap(
            common, 'open_new_tab_in_browser_if_possible', mock_open_tab)
        with flush_memcache_swap, open_tab_swap:
            deploy.flush_memcache('oppiaserver')
        self.assertEqual(check_function_calls, expected_check_function_calls)

    def test_unsuccessful_flush_memcache(self):
        def mock_flush_memcache(unused_app_name):
            return False
        check_function_calls = {
            'open_tab_gets_called': False
        }
        expected_check_function_calls = {
            'open_tab_gets_called': True
        }
        def mock_open_tab(unused_url):
            check_function_calls['open_tab_gets_called'] = True
        flush_memcache_swap = self.swap(
            gcloud_adapter, 'flush_memcache', mock_flush_memcache)
        open_tab_swap = self.swap(
            common, 'open_new_tab_in_browser_if_possible', mock_open_tab)
        with flush_memcache_swap, open_tab_swap:
            deploy.flush_memcache('oppiaserver')
        self.assertEqual(check_function_calls, expected_check_function_calls)

    def test_version_switch(self):
        check_function_calls = {
            'switch_version_gets_called': False,
        }
        expected_check_function_calls = {
            'switch_version_gets_called': True
        }
        def mock_switch_version(
                unused_app_name, unused_current_release_version):
            check_function_calls['switch_version_gets_called'] = True
        switch_version_swap = self.swap(
            gcloud_adapter, 'switch_version', mock_switch_version)
        with self.open_tab_swap, switch_version_swap, self.input_swap:
            deploy.switch_version('oppiaserver', '1-2-3')
        self.assertEqual(check_function_calls, expected_check_function_calls)

    def test_library_page_not_loading_correctly(self):
        check_function_calls = {
            'switch_version_gets_called': False,
        }
        expected_check_function_calls = {
            'switch_version_gets_called': False
        }
        def mock_switch_version(
                unused_app_name, unused_current_release_version):
            check_function_calls['switch_version_gets_called'] = True
        def mock_input():
            return 'n'
        switch_version_swap = self.swap(
            gcloud_adapter, 'switch_version', mock_switch_version)
        input_swap = self.swap(python_utils, 'INPUT', mock_input)
        with self.open_tab_swap, switch_version_swap, input_swap:
            with self.assertRaisesRegexp(
                Exception,
                'Aborting version switch due to issues in library page '
                'loading.'):
                deploy.switch_version('oppiaserver', '1-2-3')
        self.assertEqual(check_function_calls, expected_check_function_calls)

    def test_no_breakage_check_is_done_for_oppiaserver(self):
        check_function_calls = {
            'open_tab_gets_called': False
        }
        expected_check_function_calls = {
            'open_tab_gets_called': False
        }
        def mock_open_tab(unused_url):
            check_function_calls['open_tab_gets_called'] = True
        open_tab_swap = self.swap(
            common, 'open_new_tab_in_browser_if_possible', mock_open_tab)
        with self.get_version_swap, self.input_swap, open_tab_swap:
            deploy.check_breakage('oppiaserver', '1.2.3')
        self.assertEqual(check_function_calls, expected_check_function_calls)

    def test_no_breakage_check_for_oppiatestserver(self):
        with self.get_version_swap, self.input_swap, self.open_tab_swap:
            with self.assertRaisesRegexp(
                Exception,
                'Please note the issue in the release journal for this month, '
                'file a blocking bug and switch to the last known good '
                'version.'):
                deploy.check_breakage('oppiatestserver', '1.2.3')

    def test_no_breakage_check_for_migration_app(self):
        with self.get_version_swap, self.input_swap, self.open_tab_swap:
            with self.assertRaisesRegexp(
                Exception,
                'Please note the issue in the release journal for this month, '
                'file a blocking bug and switch to the last known good '
                'version.'):
                deploy.check_breakage('oppia-migration', '1.2.3')
