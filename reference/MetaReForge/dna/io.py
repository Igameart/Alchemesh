from .libimport import dna


def get_reader(path: str):
    if dna is None:
        return None
    stream = dna.FileStream(path, dna.FileStream.AccessMode_Read, dna.FileStream.OpenMode_Binary)
    reader = dna.BinaryStreamReader(stream, dna.DataLayer_All)
    reader.read()
    if not dna.Status.isOk():
        status = dna.Status.get()
        raise RuntimeError(f"Error loading DNA: {status.message}")
    return reader


def get_writer(reader, path):
    if dna is None:
        return
    stream = dna.FileStream(path, dna.FileStream.AccessMode_Write, dna.FileStream.OpenMode_Binary)
    writer = dna.BinaryStreamWriter(stream)
    writer.setFrom(reader)

    if not dna.Status.isOk():
        status = dna.Status.get()
        raise RuntimeError(f"Error saving DNA: {status.message}")
    return writer