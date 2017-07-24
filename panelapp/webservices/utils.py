def convert_moi(moi):
    short_terms = {
        "MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted": "monoallelic_not_imprinted",
        "MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)": "monoallelic_maternally_imprinted",  # noqa
        "MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)": "monoallelic_paternally_imprinted",  # noqa
        "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown": "monoallelic",
        "BIALLELIC, autosomal or pseudoautosomal": "biallelic",
        "BOTH monoallelic and biallelic, autosomal or pseudoautosomal": "monoallelic_and_biallelic",
        "BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal": "monoallelic_and_more_severe_biallelic",  # noqa
        "X-LINKED: hemizygous mutation in males, biallelic mutations in females": "xlinked_biallelic",
        "X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)": "xlinked_monoallelic",  # noqa
        "MITOCHONDRIAL": "mitochondrial",
        "Unknown": "unknown"
    }
    if moi in short_terms:
        return short_terms[moi]
    else:
        return moi


def convert_gel_status(gel_status):
    if gel_status > 2:
        return "HighEvidence"
    elif gel_status == 2:
        return "ModerateEvidence"
    elif gel_status == 0:
        return "NoList"
    else:
        return "LowEvidence"


def make_null(value):
    if not value or value == [""]:
        return None
    else:
        return value
