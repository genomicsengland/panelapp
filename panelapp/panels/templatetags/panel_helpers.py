from enum import Enum
from django import template
register = template.Library()


gene_list_data = (
    ('gel-added', 'No list', 'No list'),
    ('gel-red', 'Red List (low evidence)', 'Red'),
    ('gel-amber', 'Amber List (moderate evidence)', 'Amber'),
    ('gel-green', 'Green List (high evidence)', 'Green'),
)


class GeneStatus(Enum):
    NOLIST = 0
    RED = 1
    AMBER = 2
    GREEN = 3


class GeneDataType(Enum):
    CLASS = 0
    LONG = 1
    SHORT = 2


def get_gene_list_data(gene, list_type):
    if gene.status > 2:
        return gene_list_data[GeneStatus.GREEN.value][list_type]
    elif gene.status == 2:
        return gene_list_data[GeneStatus.AMBER.value][list_type]
    elif gene.status == 1:
        return gene_list_data[GeneStatus.RED.value][list_type]
    else:
        return gene_list_data[GeneStatus.NOLIST.value][list_type]


@register.filter
def gene_list_class(gene):
    return get_gene_list_data(gene, GeneDataType.CLASS.value)


@register.filter
def gene_list_name(gene):
    return get_gene_list_data(gene, GeneDataType.LONG.value)


@register.filter
def gene_list_short_name(gene):
    return get_gene_list_data(gene, GeneDataType.SHORT.value)


@register.filter
def gene_reviewd_by(gene, user):
    return gene.is_reviewd_by_user(user)

@register.filter
def reviewed_by(gene, user):
    return True if gene.is_reviewd_by_user(user) else False
