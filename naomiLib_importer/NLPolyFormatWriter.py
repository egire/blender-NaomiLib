from NLPolyFormatReader import NLReader

class NLWriter:
    def __init__(self, reader : NLReader = None):
        self.__reader = reader
        self.nl_polyformat
        if reader:
            self.set_reader(reader)

    def set_reader(self, reader : NLReader):
        self.nl_polyformat = reader.read()

    def write(self, file_path):
        if (not self.nl_polyformat):
            raise ValueError("No NLPolyFormat object to write")
        packed_data = self.nl_polyformat.pack()
        with open(file_path, 'wb') as file:
            file.write(packed_data)
