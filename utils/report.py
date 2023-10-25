
class Report:
    _instance = None

    def __init__(self):
        self.messages = []
        self.to_dos = []

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = Report()
        return cls._instance

    def add_message(self, message):
        self.messages.append(message)

    def add_to_do(self, to_do):
        self.to_dos.append(to_do)

    def get_messages(self):
        return self.messages

    def get_to_dos(self):
        return self.to_dos

    def __repr__(self):
        lines = ["Report for MediaManager run"]
        if len(self.messages) == 0 and len(self.to_dos) == 0:
            lines.append("Everything went fine :)")
        else:
            if len(self.messages) > 0:
                lines.append("Messages:")
                for message in self.messages:
                    lines.append(f"\t - {message}")
            if len(self.to_dos) > 0:
                lines.append("ToDos:")
                for to_do in self.to_dos:
                    lines.append(f"\t [ ] {to_do}")
        return "\n".join(lines)
