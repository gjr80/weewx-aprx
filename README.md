# APRX extension #

## Description ##

The *APRX* extension generates an APRS compliant weather beacon file. The extension consists of a single WeeWX service that generates the weather beacon file.

## Pre-requisites ##

The *APRX* extension requires WeeWX v3.0.0 or g*rea*ter and when used with WeeWX v4.0.0 or later can be used under Python 2 or Python 3.

## Installation ##

The *APRX* extension can be installed manually or automatically using the *wee_extension* utility. The preferred method of installation is through the use of *wee_extension*.

**Note:**   Symbolic names are used below to refer to some file location on the WeeWX system. These symbolic names allow a common name to be used to refer to a directory that may be different from system to system. The following symbolic names are used below:

-   *$DOWNLOAD_ROOT*. The path to the directory containing the downloaded *APRX* extension.

-   *$BIN_ROOT*. The path to the directory where WeeWX executables are located. This directory varies depending on WeeWX installation method. Refer to [where to find things](http://weewx.com/docs/usersguide.htm#Where_to_find_things "where to find things") in the WeeWX [User's Guide](http://weewx.com/docs/usersguide.htm "User's Guide to the WeeWX Weather System") for further information.

### Installation using the wee_extension utility ###

1.  Download the latest *APRX* extension from the *APRX* extension [releases page](https://github.com/gjr80/weewx-aprx/releases) into a directory accessible from the WeeWX machine.

        $ wget -P $DOWNLOAD_ROOT https://github.com/gjr80/weewx-aprx/releases/download/v0.2.0/aprx-0.2.0.tar.gz

    where *$DOWNLOAD_ROOT* is the path to the directory where the *APRX* extension is to be downloaded.

2.  Install the *APRX* extension downloaded at step 1 using the *wee_extension* utility:

        $ wee_extension --install=$DOWNLOAD_ROOT/aprx-0.2.0.tar.gz

    This will result in output similar to the following:

        Request to install '/var/tmp/aprx-0.2.0.tar.gz'
        Extracting from tar archive /var/tmp/aprx-0.2.0.tar.gz
        Saving installer file to /home/weewx/bin/user/installer/Aprx
        Saved configuration dictionary. Backup copy at /home/weewx/weewx.conf.20200412124410
        Finished installing extension '/var/tmp/aprx-0.2.0.tar.gz'

3.  Restart WeeWX:

        $ sudo /etc/init.d/weewx restart

    or

        $ sudo service weewx restart
        
    or
    
        $ sudo systemctl restart weewx

This will result in the beacon file being generated on receipt of each loop packet. A default installation will result in the generated beacon file being placed in the */var/tmp* directory. The *APRX* extension installation can be further customized (eg file locations, frequency of generation etc) by referring to the *APRX* extension wiki.

### Manual installation ###

1.  Download the latest *APRX* extension from the *APRX* extension [releases page](https://github.com/gjr80/weewx-aprx/releases) into a directory accessible from the WeeWX machine.
         
        $ wget -P $DOWNLOAD_ROOT https://github.com/gjr80/weewx-aprx/releases/download/v0.2.0/aprx-0.2.0.tar.gz
 
   where *$DOWNLOAD_ROOT* is the path to the directory where the *APRX* extension is to be downloaded.

2.  Unpack the extension as follows:

        $ tar xvfz aprx-0.2.0.tar.gz

3.  Copy files from within the resulting directory as follows:

        $ cp aprx/bin/user/aprx.py $BIN_ROOT/user

    replacing the symbolic name *$BIN_ROOT* with the nominal locations for your installation.

4.  Edit *weewx.conf*:

        $ vi weewx.conf

5.  In *weewx.conf*, modify the *[Engine] [[Services]]* section by adding the *WeewxAprx* service to the list of process services to be run:

        [Engine]
            [[Services]]

                process_services = .., user.aprx.WeewxAprx

6.  Restart WeeWX:

        $ sudo /etc/init.d/weewx restart

    or

        $ sudo service weewx restart

    or

        $ sudo systemctl restart weewx

This will result in the beacon file being generated on receipt of each loop packet. A default installation will result in the generated beacon file being placed in the */var/tmp* directory. The *APRX* extension installation can be further customized (eg file locations, frequency of generation etc) by referring to the *APRX* extension wiki.

## Support ##

General support issues may be raised in the Google Groups [weewx-user forum](https://groups.google.com/group/weewx-user "Google Groups weewx-user forum"). Specific bugs in the *APRX* extension code should be the subject of a new issue raised via the [Issues Page](https://github.com/gjr80/weewx-aprx/issues "APRX extension Issues").

## Licensing ##

The *APRX* extension is licensed under the [GNU Public License v3](https://github.com/gjr80/weewx-aprx/blob/master/LICENSE "*APRX* extension License").
