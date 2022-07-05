"""
aprx.py

A WeeWX service to generate an APRS weather packet file.

Based on the WeeWX cwxn service copyright (C) Matthew Wall 2014
(https://github.com/weewx/weewx/wiki/cwxn) and modified by
Mohd Hamid Misnan to produce the weewx2aprx service in 2015
(https://9m2tpt.blogspot.com/2015/09/getting-your-fine-offset-wx-on-rf-with.html).

Copyright (C) 2020-2022 Gary Roderick               gjroderick<at>gmail.com

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see https://www.gnu.org/licenses/.

  Version: 0.3.0                                      Date: ?? July 2022

  Revision History
    ?? July 2022        v0.3.0
        - output units can now be specified collectively or individually using
          the unit_system option or one or more xxxx_units options
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

    # Units to use in the weather packet file. Units may be specified
    # collectively through use of the unit_system option or individually
    # through one or more xxxx_units options. If the unit_system option is
    # omitted and no xxxx_units options are specified US units are used.

    # unit_system specifies the WeeWX unit system to use for data in the
    # weather packet file. Units associated with each unit system are detailed
    # in the Units appendix to the WeeWX Customization Guide. Optional, default US.
    unit_system = (US | METRIC | METRICWX)

    # individual observation group units can be controlled with one or more
    # xxxx_units options. xxxx_units options override any units specified via
    # the unit_system option. Optional, no default.
    temperature_units = (degree_C | degree_F | degree_K)
    pressure_units = (hPa | mbar | inHg)
    speed_units = (meter_per_second | mile_per_hour | km_per_hour | knot)
    rain_units = (mm | inch)

Further installation and configuration instructions can be found in the
readme.txt file included in the extension package or via weewx-aprx wiki
(https://github.com/gjr80/weewx-aprx/wiki).
"""

# python imports
import datetime
import math
import time
from distutils.version import StrictVersion

import six

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


APRX_VERSION = "0.3.0"
REQUIRED_WEEWX_VERSION = "3.0.0"
UNITS_BY_UNIT_GROUP = {'group_temperature': ('degree_C', 'degree_F', 'degree_K'),
                       'group_pressure': ('hPa', 'kPa', 'inHg', 'mmHg', 'mbar'),
                       'group_speed': ('km_per_hour', 'mile_per_hour', 'knot', 'meter_per_second'),
                       'group_rain': ('mm', 'cm', 'inch')
                       }

if StrictVersion(weewx.__version__) < StrictVersion(REQUIRED_WEEWX_VERSION):
    msg = "%s requires WeeWX %s or greater, found %s" % (''.join(('WeeWX APRX ', APRX_VERSION)),
                                                         REQUIRED_WEEWX_VERSION,
                                                         weewx.__version__)
    raise weewx.UnsupportedFeature(msg)


def nullproof(value):
    """Replace a None value with 0."""

    # if the value is not None then return the value otherwise return 0
    if value is not None:
        return value
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
        # Get the units we are to use. The user may specify units in one of two
        # ways:
        # - by specifying the WeeWX unit system to use via the unit_system
        #   config option
        # - by specifying individual group units (eg temperature, pressure etc)
        #   via xxxx_units config options
        # If a unit system is specified via the unit_system config option and
        # one or more xxxx_units config options are specified then the
        # xxxx_units config options will override the respective units in the
        # chosen unit system. If neither unit_system or any xxxx_units options
        # are set the database unit system will be used.

        # do we have a unit system ?
        unit_system_name = d.get('unit_system')
        if unit_system_name is not None:
            if unit_system_name.upper() in weewx.units.unit_constants:
                loginf("Units will be displayed using '%s' units" % unit_system_name.upper())
                unit_system = weewx.units.unit_constants[unit_system_name.upper()]
            else:
                logerr("Unknown unit_system '%s'" % unit_system_name)
                unit_system = None
        else:
            # no unit system was set
            unit_system = None

        # now get any overrides to the display units
        self.units = dict()
        for unit_group, units in six.iteritems(UNITS_BY_UNIT_GROUP):
            group = unit_group.split('_', 1)[1]
            group_key = '%s_units' % group
            if group_key in d:
                if d[group_key] in units:
                    loginf("'%s' units will be displayed as '%s'" % (group, d[group_key]))
                    self.units[unit_group] = d[group_key]
                else:
                    logerr("Unknown unit '%s' for '%s'" % (d[group_key], group))
            else:
                # no unit group override was specified, so look to the unit
                # system
                if unit_system is not None:
                    # a unit system was specified so obtain the unit group from
                    # there
                    self.units[unit_group] = weewx.units.std_groups[unit_system][unit_group]
                else:
                    # no unit system was specified so we will use the database
                    # units
                    pass

        # get the database binding to use, default to 'wx_binding'
        data_binding = d.get('data_binding', 'wx_binding')
        # now get a db manager
        self.dbm = self.engine.db_binder.get_manager(data_binding)
        # get our db rain units
        if self.dbm.std_unit_system is not None:
            self.rain_unit = weewx.units.getStandardUnitType(self.dbm.std_unit_system,
                                                             'rain')
        else:
            self.rain_unit = None
        # Do we generate our output every loop packet or every archive
        # record? 'loop' may be problematic for partial packet stations.
        binding = d.get('binding', 'loop').lower()
        if binding == 'loop':
            self.bind(weewx.NEW_LOOP_PACKET, self.process_loop_packet)
            interval_str = 'loop packet'
        else:
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.process_archive_record)
            interval_str = 'archive record'
        # now log what we are going to do/use
        loginf("version %s" % APRX_VERSION)
        loginf("using lat=%s lon=%s" % (self.lat, self.lon))
        loginf("using note=%s" % self.note)
        loginf("using symbol=%s" % self.symbol)
        loginf("using database binding '%s'" % data_binding)
        loginf("output will be saved to '%s' on every %s" % (self.filename, interval_str))

    def process_loop_packet(self, event):
        """Process a new loop packet."""

        self.process_packet(event.packet)

    def process_archive_record(self, event):
        """Process a new archive record."""

        self.process_packet(event.record)

    def process_packet(self, packet):
        """Process a data packet/record and generate a weather packet file."""

        # wrap in a try..except in case anything goes wrong
        try:
            # obtain the data required for the weather packet file
            data = self.calculate(packet)
            # generate the weather packet file
            self.write_data(data)
        except Exception as e:
            # an exception occurred, log it and continue
            log_traceback_error(prefix='aprx: **** ')

    def convert(self, value_vt):
        """Convert a ValueTuple to the destination units for that group."""

        # get the unit group  from our ValueTuple, we need it to identify our
        # destination unit
        unit_group = value_vt.group
        # do the conversion and return the resulting ValueTuple
        return weewx.units.convert(value_vt, self.units[unit_group])

    def calculate(self, packet):
        """Obtain the data for the weather packet file."""

        # obtain the group units used by the packet
        # first get the packet unit system
        packet_units = packet.get('usUnits')
        speed_unit = weewx.units.getStandardUnitType(packet_units, 'windSpeed')
        temp_unit = weewx.units.getStandardUnitType(packet_units, 'outTemp')
        press_unit = weewx.units.getStandardUnitType(packet_units, 'barometer')
        rain_unit = weewx.units.getStandardUnitType(packet_units, 'rain')
        # initialise a dict to hold out data
        data = dict()
        # the unix epoch timestamp of our data
        data['dateTime'] = packet['dateTime']
        # wind direction
        data['windDir'] = nullproof(packet.get('windDir'))
        # wind speed
        wind_speed_vt = weewx.units.ValueTuple(packet.get('windSpeed'),
                                               speed_unit,
                                               'group_speed')
        wind_speed_conv = self.convert(wind_speed_vt)
        data['windSpeed'] = nullproof(wind_speed_conv)
        # wind gust
        gust_speed_vt = weewx.units.ValueTuple(packet.get('windGust'),
                                               speed_unit,
                                               'group_speed')
        gust_speed_conv = self.convert(gust_speed_vt)
        data['windGust'] = nullproof(gust_speed_conv)
        # temperature
        temp_vt = weewx.units.ValueTuple(packet.get('outTemp'),
                                         temp_unit,
                                         'group_temperature')
        temp_conv = self.convert(temp_vt)
        data['outTemp'] = nullproof(temp_conv)
        # total rainfall in the last hour
        if 'hourRain' in packet:
            last_hr_rain_vt = weewx.units.ValueTuple(packet['hourRain'],
                                                     rain_unit,
                                                     'group_rain')
        else:
            if self.ds_aware:
                # get a timedelta object representing the period length
                _delta = datetime.timedelta(hours=1)
                # determine the start time as a datetime object
                start_td = datetime.datetime.fromtimestamp(data['dateTime']) - _delta
                # and convert to a timestamp
                start_ts = time.mktime(start_td.timetuple())
            else:
                # ignore daylight saving and simply subtract the period length
                # from the stop timestamp
                start_ts = data['dateTime'] - 3600
            last_hr_rain = self.calc_rain_in_period(start_ts, data['dateTime'])
            last_hr_rain_vt = weewx.units.ValueTuple(last_hr_rain,
                                                     self.rain_units,
                                                     'group_rain')
        last_hr_rain_conv = self.convert(last_hr_rain_vt)
        data['hourRain'] = nullproof(last_hr_rain_conv)
        # total rainfall in the last 24 hours
        if 'rain24' in packet:
            last_24_rain_vt = weewx.units.ValueTuple(packet['rain24'],
                                                     rain_unit,
                                                     'group_rain')
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
            last_24_rain = self.calc_rain_in_period(start_ts, data['dateTime'])
            last_24_rain_vt = weewx.units.ValueTuple(last_24_rain,
                                                     self.rain_units,
                                                     'group_rain')
        last_24_rain_conv = self.convert(last_24_rain_vt)
        data['rain24'] = nullproof(last_24_rain_conv)
        # total rainfall since midnight in inches
        if 'dayRain' in packet:
            day_rain_vt = weewx.units.ValueTuple(packet['dayRain'],
                                                 rain_unit,
                                                 'group_rain')
        else:
            start_ts = weeutil.weeutil.startOfDay(data['dateTime'])
            day_rain = self.calc_rain_in_period(start_ts, data['dateTime'])
            day_rain_vt = weewx.units.ValueTuple(day_rain,
                                                 self.rain_units,
                                                 'group_rain')
        day_rain_conv = self.convert(day_rain_vt)
        data['dayRain'] = nullproof(day_rain_conv)
        # humidity
        data['outHumidity'] = nullproof(packet.get('outHumidity'))
        # barometer
        baro_vt = weewx.units.ValueTuple(packet.get('barometer'),
                                         press_unit,
                                         'group_pressure')
        baro_conv = self.convert(baro_vt)
        data['barometer'] = nullproof(baro_conv)
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
        at stop_ts. Value is returned in database units
        """

        # query the database
        val = self.dbm.getSql("SELECT SUM(rain) FROM %s "
                              "WHERE dateTime>? AND dateTime<=?" % self.dbm.table_name,
                              (start_ts, stop_ts))
        # return None if no data otherwise return the query result
        if val is None:
            return None
        return val[0]
