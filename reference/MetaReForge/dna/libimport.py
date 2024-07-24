import traceback

try:
    from ..third_party.dnacalib import dna
    from ..third_party.dnacalib import dnacalib
    DNA_IMPORT_EX = None
    is_fake = False
except (ImportError, NameError) as ex:
    print(traceback.format_exc())
    from . import fake_dnacalib as dnacalib
    from . import fake_dna as dna
    DNA_IMPORT_EX = ex
    is_fake = True

try:
    from ..third_party.dnacalib import vtx_color
except (ImportError, NameError) as ex:
    vtx_color = None
