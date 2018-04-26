# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2017 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014-2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
# Copyright (c) 2017 Kurt Kanzenbach <kurt@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import os
import gpgme

from apt.package import FetchError
from shutil import rmtree
from io import BytesIO

from elbepack.repomanager import UpdateRepo
from elbepack.rpcaptcache import get_rpcaptcache
from elbepack.shellhelper import CommandError


class FinetuningAction(object):

    actiondict = {}

    @classmethod
    def register(cls, action):
        cls.actiondict[action.tag] = action

    def __new__(cls, node):
        action = cls.actiondict[node.tag]
        return object.__new__(action)

    def __init__(self, node):
        self.node = node


class RmAction(FinetuningAction):

    tag = 'rm'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        files = target.glob(self.node.et.text)

        if 'exclude' in self.node.et.attrib:
            exclude = self.node.et.attrib['exclude'].split(' ')
        else:
            exclude = []

        for f in files:
            if os.path.basename(f) in exclude:
                continue

            log.do("rm -rvf '%s'" % f)


FinetuningAction.register(RmAction)


class MkdirAction(FinetuningAction):

    tag = 'mkdir'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do("mkdir -p " + target.fname(self.node.et.text))


FinetuningAction.register(MkdirAction)


class MknodAction(FinetuningAction):

    tag = 'mknod'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do(
            "mknod " +
            target.fname(
                self.node.et.text) +
            " " +
            self.node.et.attrib['opts'])


FinetuningAction.register(MknodAction)


class BuildenvMkdirAction(FinetuningAction):

    tag = 'buildenv_mkdir'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        log.do("mkdir -p " + buildenv.rfs.fname(self.node.et.text))


FinetuningAction.register(BuildenvMkdirAction)


class CpAction(FinetuningAction):

    tag = 'cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("cp -av " + f + " " + target.fname(self.node.et.text))


FinetuningAction.register(CpAction)


class BuildenvCpAction(FinetuningAction):

    tag = 'buildenv_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        src = buildenv.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("cp -av " + f + " " + buildenv.rfs.fname(self.node.et.text))


FinetuningAction.register(BuildenvCpAction)


class B2TCpAction(FinetuningAction):

    tag = 'b2t_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        src = buildenv.rfs.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("cp -av " + f + " " + target.fname(self.node.et.text))


FinetuningAction.register(B2TCpAction)


class T2BCpAction(FinetuningAction):

    tag = 't2b_cp'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("cp -av " + f + " " + buildenv.rfs.fname(self.node.et.text))


FinetuningAction.register(T2BCpAction)


class T2PMvAction(FinetuningAction):

    tag = 't2p_mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        if self.node.et.text[0] == '/':
            dest = self.node.et.text[1:]
        else:
            dest = self.node.et.text
        dest = os.path.join('..', dest)

        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("mv -v " + f + " " + dest)


FinetuningAction.register(T2PMvAction)


class MvAction(FinetuningAction):

    tag = 'mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        src = target.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("mv -v " + f + " " + target.fname(self.node.et.text))


FinetuningAction.register(MvAction)


class LnAction(FinetuningAction):

    tag = 'ln'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with target:
            log.chroot(
                target.path, """/bin/sh -c 'ln -s %s "%s"' """ %
                (self.node.et.attrib['path'], self.node.et.text))


FinetuningAction.register(LnAction)


class BuildenvMvAction(FinetuningAction):

    tag = 'buildenv_mv'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        src = buildenv.rfs.glob(self.node.et.attrib['path'])
        for f in src:
            log.do("mv -v " + f + " " + buildenv.rfs.fname(self.node.et.text))


FinetuningAction.register(BuildenvMvAction)


class AddUserAction(FinetuningAction):

    tag = 'adduser'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with target:
            att = self.node.et.attrib
            options = ""
            if 'groups' in att:
                options += '-G "%s" ' % att['groups']
            if 'shell' in att:
                options += '-s "%s" ' % att['shell']
            if 'uid' in att:
                options += '-u "%s" ' % att['uid']
            if 'gid' in att:
                options += '-g "%s" ' % att['gid']
            if 'home' in att:
                options += '-d "%s" ' % att['home']
            if 'system' in att and att['system'] == 'True':
                options += '-r'
            if 'create_home' in att and att['create_home'] == 'False':
                options += '-M '
            else:
                options += '-m '
            if 'create_group' in att and att['create_group'] == 'False':
                options += '-N '
            else:
                options += '-U '

            log.chroot(
                target.path,
                '/usr/sbin/useradd %s "%s"' %
                (options,
                 self.node.et.text))

            if 'passwd' in att:
                log.chroot(target.path,
                           """/bin/sh -c 'echo "%s\\n%s\\n" | passwd %s'""" % (
                               att['passwd'],
                               att['passwd'],
                               self.node.et.text))


FinetuningAction.register(AddUserAction)


class AddGroupAction(FinetuningAction):

    tag = 'addgroup'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with target:
            att = self.node.et.attrib
            # we use -f always
            options = "-f "
            if 'gid' in att:
                options += '-g "%s" ' % att['gid']
            if 'system' in att and att['system'] == 'True':
                options += '-r'
            log.chroot(target.path, '/usr/sbin/groupadd %s "%s"' % (
                options,
                self.node.et.text))


FinetuningAction.register(AddGroupAction)


class RawCmdAction(FinetuningAction):

    tag = 'raw_cmd'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with target:
            log.chroot(target.path, self.node.et.text)


FinetuningAction.register(RawCmdAction)


class CmdAction(FinetuningAction):

    tag = 'command'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with target:
            log.chroot(target.path, "/bin/sh", input=self.node.et.text)


FinetuningAction.register(CmdAction)


class BuildenvCmdAction(FinetuningAction):

    tag = 'buildenv_command'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with buildenv:
            log.chroot(buildenv.path, "/bin/sh", input=self.node.et.text)


FinetuningAction.register(BuildenvCmdAction)


class PurgeAction(FinetuningAction):

    tag = 'purge'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):
        with target:
            log.chroot(target.path, "dpkg --purge " + self.node.et.text)


FinetuningAction.register(PurgeAction)


class UpdatedAction(FinetuningAction):

    tag = 'updated'

    def __init__(self, node):
        FinetuningAction.__init__(self, node)

    def execute(self, log, buildenv, target):

        if self.node.et.text:
            fp = self.node.et.text
            log.printo("transfer gpg key to target: " + fp)

            os.environ['GNUPGHOME'] = "/var/cache/elbe/gnupg"
            key = BytesIO()
            ctx = gpgme.Context()
            ctx.armor = True
            ctx.export(fp, key)

            log.printo(str(key.getvalue()))
            with open((target.path + '/pub.key'), 'wb') as tkey:
                tkey.write(key.getvalue())

            target.mkdir_p("/var/cache/elbe/gnupg", mode=0o700)
            with target:
                os.environ['GNUPGHOME'] = target.path + "/var/cache/elbe/gnupg"
                log.do("gpg --import " + target.path + "/pub.key")

        log.printo("generate base repo")
        arch = target.xml.text("project/arch", key="arch")

        buildenv.rfs.mkdir_p('/tmp/pkgs')
        with buildenv:
            cache = get_rpcaptcache(buildenv.rfs, "updated-repo.log", arch)

            pkglist = cache.get_installed_pkgs()
            for pkg in pkglist:
                try:
                    cache.download_binary(
                        pkg.name, '/tmp/pkgs', pkg.installed_version)
                except ValueError as ve:
                    log.printo(
                        "No Package " +
                        pkg.name +
                        "-" +
                        pkg.installed_version)
                except FetchError as fe:
                    log.printo(
                        "Package " +
                        pkg.name +
                        "-" +
                        pkg.installed_version +
                        " could not be downloaded")
                except TypeError as te:
                    log.printo(
                        "Package " +
                        pkg.name +
                        "-" +
                        pkg.installed_version +
                        " missing name or version")

        r = UpdateRepo(target.xml,
                       target.path + '/var/cache/elbe/repos/base',
                       log)

        for d in buildenv.rfs.glob('tmp/pkgs/*.deb'):
            r.includedeb(d, 'main')
        r.finalize()

        slist = target.path + '/etc/apt/sources.list.d/base.list'
        slist_txt = 'deb [trusted=yes] file:///var/cache/elbe/repos/base '
        slist_txt += target.xml.text("/project/suite")
        slist_txt += " main"

        with open(slist, 'w') as apt_source:
            apt_source.write(slist_txt)

        rmtree(buildenv.rfs.path + '/tmp/pkgs')

        # allow downgrades by default
        target.touch_file('/var/cache/elbe/.downgrade_allowed')


FinetuningAction.register(UpdatedAction)


def do_finetuning(xml, log, buildenv, target):

    if not xml.has('target/finetuning'):
        return

    for i in xml.node('target/finetuning'):
        try:
            action = FinetuningAction(i)
            action.execute(log, buildenv, target)
        except KeyError:
            print("Unimplemented finetuning action '%s'" % (i.et.tag))
        except CommandError:
            log.printo("Finetuning Error, trying to continue anyways")
