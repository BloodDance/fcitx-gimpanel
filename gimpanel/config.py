import ConfigParser

class RawConfigSetting(object):
    '''Just pass the file path'''
    def __init__(self, path, type=type):
        self._type = type

        self._path = path

        self.init_configparser()

    def _type_convert_set(self, value):
        if type(value) == bool:
            if value == True:
                value = 'true'
            elif value == False:
                value = 'false'

        # This is a hard code str type, so return '"xxx"' instead of 'xxx'
        if self._type == str:
            value = "'%s'" % value

        return value

    def _type_convert_get(self, value):
        if value == 'false':
            value = False
        elif value == 'true':
            value = True

        # This is a hard code str type, so return '"xxx"' instead of 'xxx'
        if self._type == str or type(value) == str:
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = eval(value)

        return value

    def init_configparser(self):
        self._configparser = ConfigParser.ConfigParser()
        self._configparser.read(self._path)

    def sections(self):
        return self._configparser.sections()

    def options(self, section):
        return self._configparser.options(section)

    def set_value(self, section, option, value):
        value = self._type_convert_set(value)

        if not self._configparser.has_section(section):
            self._configparser.add_section(section)

        self._configparser.set(section, option, value)
        with open(self._path, 'wb') as configfile:
            self._configparser.write(configfile)

        self.init_configparser()

    def get_value(self, section, option):
        if self._type:
            if self._type == int:
                getfunc = getattr(self._configparser, 'getint')
            elif self._type == float:
                getfunc = getattr(self._configparser, 'getfloat')
            elif self._type == bool:
                getfunc = getattr(self._configparser, 'getboolean')
            else:
                getfunc = getattr(self._configparser, 'get')

            value = getfunc(section, option)
        else:
            log.debug("No type message, so use the generic get")
            value = self._configparser.get(section, option)

        value = self._type_convert_get(value)

        return value
