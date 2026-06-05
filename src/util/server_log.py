

class ServerLog:

    def __init__(self):
        self.logs = list()

    def __getitem__(self, item):
        return self.logs[item]

    def extend(self, other:list):
        self.logs.extend(other)

    def getLenght(self):
        return len(self.logs)