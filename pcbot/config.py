from os import path
import yaml


class Config:
    """
    Creates a configuration yml file of a dictionary

    :param config: -- Initializer for dictionaries (required)
    :param filename: -- Filename for the config, specified without extension (default "config")
    """
    def __init__(self, config, filename="config"):
        self.config = config
        self.filename = "{}.yml".format(filename)

    def save(self):
        """ Write YAML formatted file of dictionary config to filename """
        f = open(self.filename, "w")
        f.write(yaml.safe_dump(self.config, encoding="utf-8", allow_unicode=True))
        f.close()

    def load(self):
        """
        Set dictionary config to loaded YAML formatted file filnename
        On first time use (or if the file has gone) save default config
        """
        if path.isfile(self.filename):
            with open(self.filename, "r") as f:
                self.config = yaml.load(f.read())
        else:
            self.save()

    def set(self, index, value):
        """
        Change the value of a config index

        :param index: any type stored in the config (required)
        :param value: any value, although dictionaries are not very well supported (required)
        """
        self.config[index] = value

    def get(self, index):
        """
        Get a value from the config or the config itself

        :param index: the index to return (not required)
        :return: config index if index is specified, else config
        """
        if index:
            return self.config.get(index)
        return self.config

    def remove(self, index):
        """
        Remove a key from the config

        :param index: index or key to remove
        :return: return value of removed key or False
        """
        return self.config.pop(index, False)
