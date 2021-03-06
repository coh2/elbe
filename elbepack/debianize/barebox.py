#!/usr/bin/env python
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2016  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

import os

from npyscreen import TitleText

from shutil import copyfile

from elbepack.directories import mako_template_dir
from elbepack.debianize.base import DebianizeBase, template

class BareBox (DebianizeBase):

    name  = "barebox"
    files = ['Kbuild', 'Kconfig', 'README', 'TODO']

    def __init__ (self):
        DebianizeBase.__init__ (self)

    def gui (self):
        self.defconfig = self.add_widget_intelligent (TitleText,
                name="defconfig:", value="imx_v7_defconfig")

        self.imgname = self.add_widget_intelligent (TitleText,
                name="Imagename:", value="barebox-phytec-phycore-imx6dl-som-nand-256mb.img")

        self.cross = self.add_widget_intelligent (TitleText,
                name="CROSS_COMPILE:", value="arm-linux-gnueabihf-")

        self.k_version = self.add_widget_intelligent (TitleText,
                name="BareboxVersion:", value="2016.10")

    def debianize (self):
        if self.deb['p_arch'] == 'armhf':
            self.deb['k_arch'] = 'arm'
        elif self.deb['p_arch'] == 'armel':
            self.deb['k_arch'] = 'arm'
        elif self.deb['p_arch'] == 'amd64':
            self.deb['k_arch'] = 'x86_64'
        else:
            self.deb['k_arch'] = self.deb['p_arch']

        self.deb['defconfig']     = self.defconfig.get_value ()
        self.deb['cross_compile'] = self.cross.get_value ()
        self.deb['k_version']     = self.k_version.get_value ()
        self.deb['imgname']       = self.imgname.get_value ()

        self.tmpl_dir = os.path.join(mako_template_dir, 'debianize/barebox')
        pkg_name = self.deb['p_name']+'-'+self.deb['k_version']

        for tmpl in ['control', 'rules']:
            with open (os.path.join('debian/', tmpl), 'w') as f:
                mako = os.path.join(self.tmpl_dir, tmpl+'.mako')
                f.write (template(mako, self.deb))

        cmd = 'dch --package barebox-' + pkg_name + \
                   ' -v ' + self.deb['p_version'] + \
                   ' --create -M -D ' + self.deb['release'] + \
                   ' "generated by elbe debianize"'
        os.system (cmd)

        copyfile (os.path.join(self.tmpl_dir, 'barebox-image.install'),
                  'debian/barebox-image-'+pkg_name+'.install')
        copyfile (os.path.join(self.tmpl_dir, 'barebox-tools.install'),
                  'debian/barebox-tools-'+pkg_name+'.install')

        self.hint = "use 'dpkg-buildpackage -a%s' to build the package" % self.deb['p_arch']

DebianizeBase.register (BareBox)
