class ImportException(Exception):
    pass


class UsersDoNotExist(ImportException):
    pass


class GenesDoNotExist(ImportException):
    pass


class UserDoesNotExist(ImportException):
    pass


class TSVIncorrectFormat(ImportException):
    pass


class GeneDoesNotExist(ImportException):
    pass


class STRDoesNotExist(ImportException):
    pass


class RegionDoesNotExist(ImportException):
    pass


class IncorrectGeneRating(ImportException):
    pass


class IsSuperPanelException(Exception):
    pass
