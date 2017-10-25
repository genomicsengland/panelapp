def convert_moi(moi, back=False):
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

    if back:
        full_term = None
        for ft, st in short_terms.items():
            if st == moi:
                full_term = ft
                break

        if not full_term:
            return moi
        return full_term

    if moi in short_terms:
        return short_terms[moi]
    else:
        return moi


def convert_mop(mop, back=False):
    short_terms = {
        'Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments': 'loss_of_function',  # noqa
        'Other - please provide details in the comments': 'other'
    }

    if back:
        full_term = None
        for ft, st in short_terms.items():
            if st == mop:
                full_term = ft
                break
        if not full_term:
            return mop
        return full_term

    if mop in short_terms:
        return short_terms[mop]
    return mop


def convert_evidences(evidence, back=False):
    short_terms = {
        "Radboud University Medical Center, Nijmegen": 'radboud_university_medical_center_nijmegen',
        "Illumina TruGenome Clinical Sequencing Services": 'illumina_trugenome_clinical_sequencing_services',
        "Emory Genetics Laboratory": 'emory_genetics_laboratory',
        "UKGTN": 'ukgtn',
        "Other": 'other',
        "Expert list": 'export_list',
        "Expert Review": 'export_review',
        "Literature": 'literature',
        "Eligibility statement prior genetic testing": 'eligibility_statement_prior_genetic_testing',
        "Research": 'research'
    }

    if back:
        full_term = None
        for ft, st in short_terms.items():
            if st == evidence:
                full_term = ft
                break
        if not full_term:
            return evidence
        return full_term

    if evidence in short_terms:
        return short_terms[evidence]
    return evidence


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
