from .elmerfs_parser import ElmerfsBenchParser, ElmerfsConvergenceParser, ElmerfsCopyTimeParser
from .filebench_parser import FileBenchParser
from .fmke_parser import FMKeClientParser, FMKePopulateParser


PARSERS = {
    'elmerfs_bench': ElmerfsBenchParser,
    'elmerfs_copy': ElmerfsCopyTimeParser,
    'elmerfs_convergence': ElmerfsConvergenceParser,

    'filebench': FileBenchParser,

    'fmke_client': FMKeClientParser,
    'fmke_pop': FMKePopulateParser,
}
