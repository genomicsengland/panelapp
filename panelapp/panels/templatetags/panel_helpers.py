import re
from enum import Enum
from django import template
from django.utils.safestring import SafeString
from panels.models import Evaluation
from panels.models import TrackRecord
register = template.Library()


gene_list_data = (
    ('gel-added', 'No list', 'No list', 'grey'),
    ('gel-red', 'Red List (low evidence)', 'Red', 'red'),
    ('gel-amber', 'Amber List (moderate evidence)', 'Amber', 'amber'),
    ('gel-green', 'Green List (high evidence)', 'Green', 'green'),
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
    COLOR = 3


def get_gene_list_data(gene, list_type, saved_gel_status=None, flagged=None):
    if saved_gel_status is not None:
        value = saved_gel_status
    else:
        value = gene.get('saved_gel_status') if isinstance(gene, dict) else gene.status
        if flagged is None:
            flagged = gene.get('flagged') if isinstance(gene, dict) else gene.flagged
    if flagged:
        return gene_list_data[GeneStatus.NOLIST.value][list_type]
    elif value > 2:
        return gene_list_data[GeneStatus.GREEN.value][list_type]
    elif value == 2:
        return gene_list_data[GeneStatus.AMBER.value][list_type]
    elif value == 1:
        return gene_list_data[GeneStatus.RED.value][list_type]
    else:
        return gene_list_data[GeneStatus.NOLIST.value][list_type]


def get_review_rating_data(review, list_type):
    if review.rating == Evaluation.RATINGS.GREEN:
        return gene_list_data[GeneStatus.GREEN.value][list_type]
    elif review.rating == Evaluation.RATINGS.AMBER:
        return gene_list_data[GeneStatus.AMBER.value][list_type]
    elif review.rating == Evaluation.RATINGS.RED:
        return gene_list_data[GeneStatus.RED.value][list_type]


@register.filter
def evaluation_rating_name(review):
    try:
        return Evaluation.RATINGS[review.rating]
    except KeyError:
        return review


@register.filter
def evaluation_rating_class(review):
    return get_review_rating_data(review, GeneDataType.CLASS.value)


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
def reviewed_by(gene, user):
    return True if user.is_authenticated and gene.is_reviewd_by_user(user) else False


@register.filter
def human_issue_type(issue_type):
    issues = issue_type.split(',')
    out_arr = []

    for issue in issues:
        try:
            out_arr.append(TrackRecord.ISSUE_TYPES[issue])
        except KeyError:
            out_arr.append(issue)

    return ", ".join(out_arr)


@register.filter
def get_ensembleId(transcripts):
    return transcripts.get('GRch38', {}).get('89', {}).get('ensembl_id', None)


@register.filter
def pubmed_link(publication):
    # Pubmed IDs are 1-8 digits, but not all strings of digits are pubmed IDs
    # Assume that 7-8 chars is a pubmed ID and link to it.
    parts = re.split('([0-9]{7,8})', publication)
    for i, part in enumerate(parts):
        if re.search('^[0-9]{7,8}$', part):
            part = SafeString('<a href="http://www.ncbi.nlm.nih.gov/pubmed/' + part + '">' + part + '</a>')
            parts[i] = part
    return parts


@register.filter
def remove_special(seq):
    return re.sub('\W+', '', seq)


@register.filter
def human_variant_types(variant_type):
    from panels.models import Region
    return Region.VARIANT_TYPES[variant_type]
