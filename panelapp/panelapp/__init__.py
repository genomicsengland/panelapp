import pkg_resources


def get_package_version():
    version = ''

    try:
        version = pkg_resources.get_distribution("panelapp").version
    except pkg_resources.DistributionNotFound:
        pass

    return version


__version__ = get_package_version()
