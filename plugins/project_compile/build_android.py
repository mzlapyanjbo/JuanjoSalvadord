#!/usr/bin/python
# build_native.py
# Build native codes


import sys
import os, os.path
import shutil
from optparse import OptionParser
import cocos
import json
import re
from xml.dom import minidom

BUILD_CFIG_FILE="build-cfg.json"

def select_toolchain_version(ndk_root):
    '''Because ndk-r8e uses gcc4.6 as default. gcc4.6 doesn't support c++11. So we should select gcc4.7 when
    using ndk-r8e. But gcc4.7 is removed in ndk-r9, so we should determine whether gcc4.7 exist.
    Conclution:
    ndk-r8e  -> use gcc4.7
    ndk-r9   -> use gcc4.8
    '''

    if os.path.isdir(os.path.join(ndk_root,"toolchains/arm-linux-androideabi-4.8")):
        os.environ['NDK_TOOLCHAIN_VERSION'] = '4.8'
        cocos.Logging.info("The Selected NDK toolchain version was 4.8 !")
    elif os.path.isdir(os.path.join(ndk_root,"toolchains/arm-linux-androideabi-4.7")):
        os.environ['NDK_TOOLCHAIN_VERSION'] = '4.7'
        cocos.Logging.info("The Selected NDK toolchain version was 4.7 !")
    else:
        message = "Couldn't find the gcc toolchain."
        raise cocos.CCPluginError(message)



def copy_files_in_dir(src, dst):

    for item in os.listdir(src):
        path = os.path.join(src, item)
        # Android can not package the file that ends with ".gz"
        if not item.startswith('.') and not item.endswith('.gz') and os.path.isfile(path):
            shutil.copy(path, dst)
        if os.path.isdir(path):
            new_dst = os.path.join(dst, item)
            os.mkdir(new_dst)
            copy_files_in_dir(path, new_dst)

def copy_dir_into_dir(src, dst):
    normpath = os.path.normpath(src)
    dir_to_create = normpath[normpath.rfind(os.sep)+1:]
    dst_path = os.path.join(dst, dir_to_create)
    shutil.copytree(src, dst_path, True)


class AndroidBuilder(object):

    CFG_KEY_COPY_TO_ASSETS = "copy_to_assets"
    CFG_KEY_MUST_COPY_TO_ASSERTS = "must_copy_to_assets"

    def __init__(self, verbose, cocos_root, app_android_root, no_res):
        self._verbose = verbose

        self.cocos_root = cocos_root
        self.app_android_root = app_android_root
        self._no_res = no_res

        self._parse_cfg()

    def _run_cmd(self, command):
        cocos.CMDRunner.run_cmd(command, self._verbose)
   
    def _parse_cfg(self):
        f = open(os.path.join(self.app_android_root, BUILD_CFIG_FILE))
        cfg = json.load(f, encoding='utf8')
        f.close()

        if cfg.has_key(AndroidBuilder.CFG_KEY_MUST_COPY_TO_ASSERTS):
            if self._no_res:
                self.res_files = cfg[AndroidBuilder.CFG_KEY_MUST_COPY_TO_ASSERTS]
            else:
                self.res_files = cfg[AndroidBuilder.CFG_KEY_MUST_COPY_TO_ASSERTS] + cfg[AndroidBuilder.CFG_KEY_COPY_TO_ASSETS]
        else:
            self.res_files = cfg[AndroidBuilder.CFG_KEY_COPY_TO_ASSETS]

        self.ndk_module_paths = cfg['ndk_module_path']

    def do_ndk_build(self, ndk_root, ndk_build_param):
        select_toolchain_version(ndk_root)

        app_android_root = self.app_android_root
        cocos_root = self.cocos_root
        ndk_path = os.path.join(ndk_root, "ndk-build")
        module_paths = [os.path.join(app_android_root, path) for path in self.ndk_module_paths]

        # windows should use ";" to seperate module paths
        if cocos.os_is_win32():
            ndk_module_path = ';'.join(module_paths)
        else:
            ndk_module_path = ':'.join(module_paths)
        
        ndk_module_path= 'NDK_MODULE_PATH=' + ndk_module_path

        if ndk_build_param == None:
            ndk_build_cmd = '%s -C %s %s' % (ndk_path, app_android_root, ndk_module_path)
        else:
            ndk_build_cmd = '%s -C %s %s %s' % (ndk_path, app_android_root, ''.join(str(e) for e in ndk_build_param), ndk_module_path)

        self._run_cmd(ndk_build_cmd)


    def _xml_attr(self, dir, file_name, node_name, attr):
        doc = minidom.parse(os.path.join(dir, file_name))
        return doc.getElementsByTagName(node_name)[0].getAttribute(attr)

    def update_lib_projects(self, sdk_root, sdk_tool_path, android_platform):
        property_file = os.path.join(self.app_android_root, "project.properties")
        if not os.path.isfile(property_file):
            return;

        patten = re.compile(r'^android\.library\.reference\.[\d]+=(.+)')
        for line in open(property_file):
            str1 = line.replace(' ', '')
            str2 = str1.replace('\t', '')
            match = patten.match(str2)
            if match is not None:
                # a lib project is found
                lib_path = match.group(1)
                abs_lib_path = os.path.join(self.app_android_root, lib_path)
                if os.path.isdir(abs_lib_path):
                    api_level = self.check_android_platform(sdk_root, android_platform, abs_lib_path, True)
                    str_api_level = "android-" + str(api_level)
                    command = "%s update lib-project -p %s -t %s" % (sdk_tool_path, abs_lib_path, str_api_level)
                    self._run_cmd(command)

    def get_target_config(self, proj_path):
        property_file = os.path.join(proj_path, "project.properties")
        if not os.path.isfile(property_file):
            raise cocos.CCPluginError("Can't find file \"%s\"" % property_file)

        patten = re.compile(r'^target=android-(\d+)')
        for line in open(property_file):
            str1 = line.replace(' ', '')
            str2 = str1.replace('\t', '')
            match = patten.match(str2)
            if match is not None:
                target = match.group(1)
                target_num = int(target)
                if target_num > 0:
                    return target_num

        raise cocos.CCPluginError("Can't find \"target\" in file \"%s\"" % property_file)

    # check the selected android platform
    def check_android_platform(self, sdk_root, android_platform, proj_path, auto_select):
        ret = android_platform
        min_platform = self.get_target_config(proj_path)
        if android_platform is None:
            # not specified platform, found one
            cocos.Logging.info('Android platform not specified, searching a default one...')
            ret = cocos.select_default_android_platform(min_platform)
        else:
            # check whether it's larger than min_platform
            if android_platform < min_platform:
                if auto_select:
                    # select one for project
                    ret = cocos.select_default_android_platform(min_platform)
                else:
                    # raise error
                    raise cocos.CCPluginError("The android-platform of project \"%s\" should be equal/larger than %d, but %d is specified." % (proj_path, min_platform, android_platform))

        if ret is None:
            raise cocos.CCPluginError("Can't find right android-platform for project : \"%s\". The android-platform should be equal/larger than %d" % (proj_path, min_platform))

        platform_path = "platforms/android-%d" % ret
        ret_path = os.path.join(sdk_root, platform_path)
        if not os.path.isdir(ret_path):
            raise cocos.CCPluginError("The directory \"%s\" can't be found in android SDK" % platform_path)

        return ret

    def do_build_apk(self, sdk_root, ant_root, android_platform, build_mode, output_dir = None):
        sdk_tool_path = os.path.join(sdk_root, "tools/android")
        cocos_root = self.cocos_root
        app_android_root = self.app_android_root

        # check the android platform
        api_level = self.check_android_platform(sdk_root, android_platform, app_android_root, False)

        # update project
        str_api_level = "android-" + str(api_level)
        command = "%s update project -t %s -p %s" % (sdk_tool_path, str_api_level, app_android_root)
        self._run_cmd(command)

        # update lib-projects
        self.update_lib_projects(sdk_root, sdk_tool_path, android_platform)

        # copy resources
        self._copy_resources()

        # run ant build
        ant_path = os.path.join(ant_root, 'ant')
        buildfile_path = os.path.join(app_android_root, "build.xml")
        command = "%s clean %s -f %s -Dsdk.dir=%s" % (ant_path, build_mode, buildfile_path, sdk_root)
        self._run_cmd(command)

        if output_dir:
             project_name = self._xml_attr(app_android_root, 'build.xml', 'project', 'name')
             if build_mode == 'release':
                apk_name = '%s-%s-unsigned.apk' % (project_name, build_mode)
             else:
                apk_name = '%s-%s-unaligned.apk' % (project_name, build_mode)

             #TODO 'bin' is hardcoded, take the value from the Ant file
             apk_path = os.path.join(app_android_root, 'bin', apk_name)
             if not os.path.exists(output_dir):
                 os.makedirs(output_dir)
             shutil.copy(apk_path, output_dir)
             cocos.Logging.info("Move apk to %s" % output_dir)


    def _copy_resources(self):
        app_android_root = self.app_android_root
        res_files = self.res_files

        # remove app_android_root/assets if it exists
        assets_dir = os.path.join(app_android_root, "assets")
        if os.path.isdir(assets_dir):
            shutil.rmtree(assets_dir)

        # copy resources
        os.mkdir(assets_dir)
        for res in res_files:
            resource = os.path.join(app_android_root, res)
            if os.path.isdir(resource):
                if res.endswith('/'):
                    copy_files_in_dir(resource, assets_dir)
                else:
                    copy_dir_into_dir(resource, assets_dir)
            elif os.path.isfile(resource):
                shutil.copy(resource, assets_dir)

