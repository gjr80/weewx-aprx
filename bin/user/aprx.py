"""
aprx.py

A WeeWX service to generate an APRS weather packet file.

Based on the WeeWX cwxn service copyright (C) Matthew Wall 2014
(https://github.com/weewx/weewx/wiki/cwxn) and modified by
Mohd Hamid Misnan to produce the weewx2aprx service in 2015
(https://9m2tpt.blogspot.com/2015/09/getting-your-fine-offset-wx-on-rf-with.html).

Copyright (C) 2020 Gary Roderick                    gjroderick<at>gmail.com

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see https://www.gnu.org/licenses/.

  Version: 0.2.1                                      Date: 11 June 2021

  Revision History
    11 June 2021        v0.2.1
        - fixed bug that resulted in date-time being displayed in local time
          rather than Zulu time/GMT
    8 June 2021         v0.2.0
        - initial release
        - day rain and 24 hour rain now derived from the WeeWX archive if not
          provided by the weather station driver
        - moved rain calculation method to class WeewxAprx()
        - latitude and longitude default to station latitude/longitude if not
          specified under [WeewxAprx] in weewx.conf
        - now WeeWX 3 and WeeWX 4/python 2 or 3 compatible
        - added daylight_saving_aware config item so that calculation of day
          rain and hour rain from archive can be daylight saving aware,
          default is False.
        - added default values for symbol and output file name
        - the WeeWX database to be used can now be specified through use of the
          data_binding config option under [WeewxAprx] in weewx.conf
        - added additional config output to log during startup
        - changed humidity output format to comply with APRS protocol

Purpose

The purpose of the weewx-aprx service is to generate an APRS compliant weather
packet file. Details of the APRS protocol can be found
at http://www.aprs.net/vm/DOS/PROTOCOL.HTM.

Abbreviated instructions for use

1.  Download the latest weewx-aprx extension package from the GitHub weewx-aprx
releases tab (https://github.com/gjr80/weewx-aprx/releases).

2.  Install the extension package using the wee_extension utility.

3.  Restart WeeWX

Detailed installation instructions can be found in the readme.txt file included
in the extension package or on the GitHub weewx-aprx home
page (https://github.com/gjr80/weewx-aprx).

Basic configuration

A default install of the weewx-aprx extension should result in a weather packet
file being produced. The operation of the weewx-aprx extension and content of
the beacon file can be customised using config settings under the [WeewxAprx]
stanza in weewx.conf as follows:

[WeewxAprx]
    # Latitude string to be used in the weather packet file. Format is:
    #   lat = ddmm.mmH
    # where:
    #   dd:    two digit latitude degree value (includes leading zeroes)
    #   mm.mm: latitude minutes rounded to two decimal places (includes leading
    #          zeroes)
    #   H:     N for northern hemisphere or S for southern hemisphere latitude
    # Optional, default is station latitude.
    lat = ddmm.mmH

    # Longitude string to be used in the weather packet file. Format is:
    #   lon = dddmm.mmH
    #   ddd:   three digit longitude degree value (includes leading zeroes)
    #   mm.mm: longitude minutes rounded to two decimal places (includes
    #          leading zeroes)
    #   H:     W for western hemisphere or E for eastern hemisphere longitude
    # Optional, default is station longitude.
    lon = dddmm.mmH

    # Symbol to use in the weather packet file. To prevent confusion when the
    # config file is parsed it is recommended that the symbol setting be
    # enclosed in single or double quotation marks. If a comma is used it must
    # be enclosed in single or double quotation marks.Optional, default is '/_'.
    symbol = '/_'

    # Note to include at the end of the weather data string. If whitespace is
    # included in the note setting then the note setting must be enclosed in
    # single or double quotation marks. Optional, default is no note string.
    note = 'note text'

    # Full path and file name used for the weather packet file output. Optional,
    # default is /var/tmp/wprx_wx.txt.
    filename = full_path_and_filename

    # Database binding to use. Optional, default 'wx_binding'.
    data_binding = binding_name

    # Whether to generate a weather packet file on the arrival of each archive
    # record or each loop packet. Format is:
    #   binding = loop|archive
    # where:
    #   loop:    generates a beacon file on the arrival of each loop packet
    #   archive: generates a beacon file on the arrival of each archive record
    # Optional, default is 'loop'.
    binding = loop|archive

    # Whether to include compensation for daylight saving when calculating
    # 24 hour rain and hour rain from the WeeWX database. Format is:
    #   daylight_saving_aware = True|False
    # where:
    #   True:  24 hour rain and hour rain calculations using the WeeWX database
    #          are compensated for daylight saving
    #   False: 24 hour rain and hour rain calculations using the WeeWX database
    #          are not compensated for daylight saving
    # Optional, default is False.
    daylight_saving_aware = True|False

Detailed configuration instructions can be found in the readme.txt file included
in the extension package or on the GitHub weewx-aprx home
page (https://github.com/gjr80/weewx-aprx).
"""

# python imports
import datetime
import math
import time
from distutils.version import StrictVersion

# WeeWX imports
import weewx
import weewx.units
import weeutil.weeutil
from weewx.engine import StdService

# import/setup logging, WeeWX v3 is syslog based but WeeWX v4 is logging based,
# try v4 logging and if it fails use v3 logging
try:
    # WeeWX4 logging
    import logging
    from weeutil.logger import log_traceback
    log = logging.getLogger(__name__)

    def logdbg(msg):
        log.debug(msg)

    def loginf(msg):
        log.info(msg)

    def logerr(msg):
        log.error(msg)

    # log_traceback() generates the same output but the signature and code is
    # different between v3 and v4. We only need log_traceback at the log.error
    # level so define a suitable wrapper function.
    def log_traceback_error(prefix=''):
        log_traceback(log.error, prefix=prefix)

except ImportError:
    # WeeWX legacy (v3) logging via syslog
    import syslog
    from weeutil.weeutil import log_traceback

    def logmsg(level, msg):
        syslog.syslog(level, 'aprx: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

    # log_traceback() generates the same output but the signature and code is
    # different between v3 and v4. We only need log_traceback at the log.error
    # level so define a suitable wrapper function.
    def log_traceback_error(prefix=''):
        log_traceback(prefix=prefix, loglevel=syslog.LOG_ERR)


APRX_VERSION = "0.2.1"
REQUIRED_WEEWX_VERSION = "3.0.0"

if StrictVersion(weewx.__version__) < StrictVersion(REQUIRED_WEEWX_VERSION):
    msg = "%s requires WeeWX %s or greater, found %s" % (''.join(('WeeWX APRX ', APRX_VERSION)),
                                                         REQUIRED_WEEWX_VERSION,
                                                         weewx.__version__)
    raise weewx.UnsupportedFeature(msg)


def convert(v, obs, group, from_unit_system, to_units):
    """Convert an observation value to the required units."""

    # get the units used by our observation given the packet unit system
    ut = weewx.units.getStandardUnitType(from_unit_system, obs)
    # express our observation as a ValueTuple
    vt = weewx.units.ValueTuple(v, ut[0], group)
    # return the value
    return weewx.units.convert(vt, to_units).value


def nullproof(key, data):
    """Replace a missing or None value packet field with 0."""

    # if the key exists in the packet and the obs is not None then return the
    # obs value otherwise return 0
    if key in data and data[key] is not None:
        return data[key]
    return 0


class WeewxAprx(StdService):
    """WeeWX service to generate an APRS weather packet file."""

    def __init__(self, engine, config_dict):
        # call our parent's initialisation
        super(WeewxAprx, self).__init__(engine, config_dict)

        # obtain our config dict
        d = config_dict.get('WeewxAprx', {})

        # obtain latitude and longitude, default to station latitude and
        # longitude
        lat = d.get('lat')
        if lat is None:
            # get the absolute value of station latitude as a float
            station_lat_abs = abs(engine.stn_info.latitude_f)
            # obtain the degrees and fractions of a degree
            (frac, degrees) = math.modf(station_lat_abs)
            # obtain number of minutes as a float
            _temp = frac * 60.0
            # obtain the minutes and fractions of a minute
            (frac_minutes, minutes) = math.modf(_temp)
            # obtain the hundredths of a minute
            decimal_minutes = frac_minutes * 100.0
            # obtain the hemisphere as a single character string
            hemi = 'N' if engine.stn_info.latitude_f >= 0.0 else 'S'
            # construct the APRS format latitude string
            lat = "%02d%02d.%02d%s" % (degrees, minutes, decimal_minutes, hemi)
        # set our latitude string property
        self.lat = lat
        lon = d.get('lon')
        if lon is None:
            # get the absolute value of station longitude as a float
            station_lon_abs = abs(engine.stn_info.longitude_f)
            # obtain the degrees and fractions of a degree
            (frac, degrees) = math.modf(station_lon_abs)
            # obtain number of minutes as a float
            _temp = frac * 60.0
            # obtain the minutes and fractions of a minute
            (frac_minutes, minutes) = math.modf(_temp)
            # obtain the hundredths of a minute
            decimal_minutes = frac_minutes * 100.0
            # obtain the hemisphere as a single character string
            hemi = 'E' if engine.stn_info.longitude_f >= 0.0 else 'W'
            # construct the APRS format longitude string
            lon = "%03d%02d.%02d%s" % (degrees, minutes, decimal_minutes, hemi)
        # set our longitude string property
        self.lon = lon
        # obtain the note to use
        self.note = d.get('note', '')
        # symbol to use
        self.symbol = d.get('symbol', '/_')
        # obtain the output file name
        self.filename = d.get('filename', '/var/tmp/aprx_wx.txt')
        # are we daylight saving aware, only used if calculating rainfall from
        # archive
        self.ds_aware = weeutil.weeutil.tobool(d.get('daylight_saving_aware',
                                                     False))
        # get the database binding to use, default to 'wx_binding'
        data_binding = d.get('data_binding', 'wx_binding')
        # now get a db manager
        self.dbm = self.engine.db_binder.get_manager(data_binding)
        # Do we generate our output every loop packet or every archive
        # record? 'loop' may be problematic for partial packet stations.
        binding = d.get('binding', 'loop').lower()
        if binding == 'loop':
            self.bind(weewx.NEW_LOOP_PACKET, self.handle_new_loop)
            interval_str = 'loop packet'
        else:
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.handle_new_archive)
            interval_str = 'archive record'
        # now log what we are going to do/use
        loginf("version %s" % APRX_VERSION)
        loginf("using lat=%s lon=%s" % (self.lat, self.lon))
        loginf("using note=%s" % self.note)
        loginf("using symbol=%s" % self.symbol)
        loginf("using database binding '%s'" % data_binding)
        loginf("output will be saved to '%s' on every %s" % (self.filename, interval_str))

    def handle_new_loop(self, event):
        """Process a new loop packet."""

        self.handle_data(event.packet)

    def handle_new_archive(self, event):
        """Process a new archive record."""

        self.handle_data(event.record)

    def handle_data(self, event_data):
        """Obtain the required data and generate the weather packet file."""

        # wrap in a try..except in case anything goes wrong
        try:
            # obtain the data required for the weather packet file
            data = self.calculate(event_data)
            # generate the weather packet file
            self.write_data(data)
        except Exception as e:
            # an exception occurred, log it and continue
            log_traceback_error(prefix='aprx: **** ')

    def calculate(self, packet):
        """Obtain the data for the weather packet file."""

        # obtain the unit system used by the packet
        pu = packet.get('usUnits')
        # initialise a dict to hold out data
        data = dict()
        # the unix epoch timestamp of our data
        data['dateTime'] = packet['dateTime']
        # wind direction
        data['windDir'] = nullproof('windDir', packet)
        v = nullproof('windSpeed', packet)
        # wind speed in mph
        data['windSpeed'] = convert(v, 'windSpeed', 'group_speed', pu, 'mile_per_hour')
        v = nullproof('windGust', packet)
        # wind gust in mph
        data['windGust'] = convert(v, 'windGust', 'group_speed', pu, 'mile_per_hour')
        # temperature in F
        v = nullproof('outTemp', packet)
        data['outTemp'] = convert(v, 'outTemp', 'group_temperature', pu, 'degree_F')
        # total rainfall in the last hour in inches
        if self.ds_aware:
            # get a timedelta object representing the period length
            _delta = datetime.timedelta(hours=1)
            # determine the start time as a datetime object
            start_td = datetime.datetime.fromtimestamp(data['dateTime']) - _delta
            # and convert to a timestamp
            start_ts = time.mktime(start_td.timetuple())
        else:
            # ignore daylight saving and simply subtract the period length from
            # the stop timestamp
            start_ts = data['dateTime'] - 3600
        v = self.calc_rain_in_period(start_ts, data['dateTime'])
        v = 0 if v is None else v
        data['hourRain'] = convert(v, 'rain', 'group_rain', pu, 'inch')
        # total rainfall in the last 24 hours in inches
        if 'rain24' in packet:
            v = nullproof('rain24', packet)
        else:
            if self.ds_aware:
                # get a timedelta object representing the period length
                _delta = datetime.timedelta(days=1)
                # determine the start time as a datetime object
                start_td = datetime.datetime.fromtimestamp(data['dateTime']) - _delta
                # and convert to a timestamp
                start_ts = time.mktime(start_td.timetuple())
            else:
                # ignore daylight saving and simply subtract the period length from
                # the stop timestamp
                start_ts = data['dateTime'] - 86400
            v = self.calc_rain_in_period(start_ts, data['dateTime'])
            v = 0 if v is None else v
        data['rain24'] = convert(v, 'rain', 'group_rain', pu, 'inch')
        # total rainfall since midnight in inches
        if 'dayRain' in packet:
            v = nullproof('dayRain', packet)
        else:
            start_ts = weeutil.weeutil.startOfDay(data['dateTime'])
            v = self.calc_rain_in_period(start_ts, data['dateTime'])
            v = 0 if v is None else v
        data['dayRain'] = convert(v, 'rain', 'group_rain', pu, 'inch')
        # humidity
        data['outHumidity'] = nullproof('outHumidity', packet)
        # barometer in mbar
        v = nullproof('barometer', packet)
        data['barometer'] = convert(v, 'pressure', 'group_pressure', pu, 'mbar')
        return data

    def write_data(self, data):
        """Generate the weather packet file.

        Construct a list of the formatted content for each field in the packet
        string. Concatenate this content and write to the weather packet file.
        """

        # initialise a list to hold the formatted fields used to construct the
        # packet string
        fields = list()
        # add the formatted fields to the field list in order
        fields.append("%s" % self.lat)
        fields.append("%s" % self.symbol[0])
        fields.append("%s" % self.lon)
        fields.append("%s" % self.symbol[1])
        fields.append("%03d" % int(data['windDir']))
        fields.append("/%03d" % int(data['windSpeed']))
        fields.append("g%03d" % int(data['windGust']))
        fields.append("t%03d" % int(data['outTemp']))
        fields.append("r%03d" % int(data['hourRain'] * 100))
        fields.append("p%03d" % int(data['rain24'] * 100))
        fields.append("P%03d" % int(data['dayRain'] * 100))
        if data['outHumidity'] < 0 or 100 <= data['outHumidity']:
            data['outHumidity'] = 0
        fields.append("h%02d" % int(data['outHumidity']))
        fields.append("b%05d" % int(data['barometer'] * 10))
        fields.append(" %s" % self.note)
        # open the output file for writing
        with open(self.filename, 'w') as f:
            # write the date-time
            f.write(time.strftime("@%d%H%Mz",
                                  time.gmtime(data['dateTime'])))
            # write the formatted fields
            f.write(''.join(fields))
            # write a terminating new line character
            f.write("\n")

    def calc_rain_in_period(self, start_ts, stop_ts):
        """Calculate rainfall in a period.

        Calculates total rainfall in a period starting at start_ts and ending
        at stop_ts.
        """

        # query the database
        val = self.dbm.getSql("SELECT SUM(rain) FROM %s "
                         "WHERE dateTime>? AND dateTime<=?" % self.dbm.table_name,
                         (start_ts, stop_ts))
        # return None if no data otherwise return the query result
        if val is None:
            return None
        return val[0]
