"""
This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

                        Installer for weewx-aprx

Version: 0.2.0                                      Date: 11 April 2020

Revision History
    11 April 2020       v0.2.0
        - initial implementation
"""

import weewx

from distutils.version import StrictVersion
from setup import ExtensionInstaller

REQUIRED_VERSION = "3.7.0"
APRX_VERSION = "0.2.0"


def loader():
    return AprxInstaller()


class AprxInstaller(ExtensionInstaller):
    def __init__(self):
        if StrictVersion(weewx.__version__) < StrictVersion(REQUIRED_VERSION):
            msg = "%s requires WeeWX %s or greater, found %s" % (''.join(('WeeWX APRX ', APRX_VERSION)),
                                                                 REQUIRED_VERSION,
                                                                 weewx.__version__)
            raise weewx.UnsupportedFeature(msg)
        super(AprxInstaller, self).__init__(
            version=APRX_VERSION,
            name='APRX',
            description='WeeWX service to generate an APRX ready beacon file.',
            author="Gary Roderick",
            author_email="gjroderick<@>gmail.com",
            files=[('bin/user', ['bin/user/aprx.py'])],
            process_services='user.aprx.WeewxAprx',
            config={
                'WeewxAprx': {
                },
            }
        )
