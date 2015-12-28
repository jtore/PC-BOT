import yaml
import os


class Config:
    def __init__(self, config, file="config.yml"):
        self.config = config
        self.default_config = self.config
        self.file = file

    def reset(self):
        self.config = self.default_config

    def save(self):
        file = open(self.file, "w")
        file.write(yaml.safe_dump(self.config, encoding="utf-8", allow_unicode=True))
        file.close()

    def load(self):
        if os.path.isfile(self.file):
            with open(self.file, "r") as file:
                self.config = yaml.load(file.read())
        else:
            self.save()

    def set(self, index, value):
        self.config[index] = value

    def get(self, value):
        if value:
            return self.config.get(value)
        return self.config
