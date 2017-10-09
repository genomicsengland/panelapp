Panelapp WebServices
====================

# List Panels

Endpoint: `https://panelapp.genomicsengland.co.uk/WebServices/list_panels/`

Returns the list of panels

```
{
    "result": [
        {
            "DiseaseGroup": "Ophthalmological disorders",
            "Number_of_Genes": 54,
            "Name": "Anophthalmia/microphthamia",
            "Panel_Id": "553f97abbb5a1616e5ed45f9",
            "CurrentVersion": "1.8",
            "DiseaseSubGroup": "Ocular malformations",
            "Relevant_disorders": [
                "Anophthalmia or microphthamia"
            ]
        }
    ]
}
```

## Filtering

Parameters:

- `Name`: Filters the list by panel name

## Examples

- https://panelapp.genomicsengland.co.uk/WebServices/list_panels/
- https://panelapp.genomicsengland.co.uk/WebServices/list_panels/?Name=Ocular%20malformations


# Get Panel Info

Endpoint `https://panelapp.genomicsengland.co.uk/WebServices/get_panel/{Panel ID | Panel Name}/`

Returns Panel info

```
{
    "result": {
        "Genes": [
            {
                "Publications": null,
                "ModeOfPathogenicity": null,
                "Evidences": [
                    "Emory Genetics Laboratory",
                    "Expert Review Green"
                ],
                "EnsembleGeneIds": [
                    "ENSG00000054598"
                ],
                "GeneSymbol": "FOXC1",
                "ModeOfInheritance": "monoallelic",
                "Phenotypes": null,
                "Penetrance": "Complete",
                "LevelOfConfidence": "HighEvidence"
            }
        ],
        "DiseaseSubGroup": "Ocular malformations",
        "version": "1.8",
        "SpecificDiseaseName": "Anophthalmia/microphthamia",
        "DiseaseGroup": "Ophthalmological disorders"
    }
}
```

## Filtering

Parameters:

- `ModeOfInheritance`: comma separated list of modes of inheritance, one of the following values:

    - `monoallelic_not_imprinted`
    - `monoallelic_maternally_imprinted`
    - `monoallelic_paternally_imprinted`
    - `monoallelic`
    - `biallelic`
    - `monoallelic_and_biallelic`
    - `monoallelic_and_more_severe_biallelic`
    - `xlinked_biallelic`
    - `xlinked_monoallelic`
    - `mitochondrial`
    - `unknown`

- `ModeOfPathogenicity`: comma separated list of modes of pathogenicities, one of the following values:

    - `loss_of_function`
    - `other`

- `Penetrance`: comma separated list of penetrance values, one of the following:

    - `unknown`
    - `Complete`
    - `Incomplete`

- `LevelOfConfidence`: comma separated list of confidence levels, one of the following:

    - `HighEvidence`
    - `ModerateEvidence`
    - `LowEvidence`

- `version`: Panel version


## Examples

- https://panelapp.genomicsengland.co.uk/WebServices/get_panel/553f97abbb5a1616e5ed45f9/
- https://panelapp.genomicsengland.co.uk/WebServices/get_panel/Anophthalmia/
- https://panelapp.genomicsengland.co.uk/WebServices/get_panel/Anophthalmia/?ModeOfInheritance=biallelic,monoallelic
- https://panelapp.genomicsengland.co.uk/WebServices/get_panel/Anophthalmia/?ModeOfPathogenicity=loss_of_function
- https://panelapp.genomicsengland.co.uk/WebServices/get_panel/Anophthalmia/?Penetrance=Complete
- https://panelapp.genomicsengland.co.uk/WebServices/get_panel/Anophthalmia/?LevelOfConfidence=HighEvidence,ModerateEvidence
- https://panelapp.genomicsengland.co.uk/WebServices/get_panel/Anophthalmia/?version=1.7
- https://panelapp.genomicsengland.co.uk/WebServices/get_panel/553f97abbb5a1616e5ed45f9/?version=1.7


# Search by Gene

Endpoint `https://panelapp.genomicsengland.co.uk/WebServices/search_genes/{Comma separated list of gene symbol}/`

```
{
    "results": [
        {
            "SpecificDiseaseName": "Insulin resistance (including lipodystrophy",
            "Publications": [
                "15166380",
                "17327441",
                "17576055"
            ],
            "Phenotypes": [
                "Diabetes mellitus, type II\t125853"
            ],
            "EnsembleGeneIds": [
                "ENSG00000105221"
            ],
            "Evidences": [
                "Expert Review Red",
                "Radboud University Medical Center, Nijmegen",
                "Emory Genetics Laboratory",
                "Literature"
            ],
            "DiseaseGroup": "Endocrine disorders",
            "ModeOfInheritance": "monoallelic_not_imprinted",
            "DiseaseSubGroup": "Disorders of unusual phenotypes",
            "LevelOfConfidence": "LowEvidence",
            "ModeOfPathogenicity": null,
            "GeneSymbol": "AKT2",
            "version": "1.2",
            "Penetrance": "Complete"
        },
        {
            "SpecificDiseaseName": "Multi-organ autoimmune diabetes",
            "Publications": null,
            "Phenotypes": [
                "Diabetes mellitus, type II, 125853",
                " Hypoinsulinemic hypoglycemia with hemihypertrophy, 240900"
            ],
            "EnsembleGeneIds": [
                "ENSG00000105221"
            ],
            "Evidences": [
                "Expert Review Removed",
                "Radboud University Medical Center, Nijmegen"
            ],
            "DiseaseGroup": "Endocrine disorders",
            "ModeOfInheritance": null,
            "DiseaseSubGroup": "Disorders of unusual phenotypes",
            "LevelOfConfidence": "NoList",
            "ModeOfPathogenicity": null,
            "GeneSymbol": "AKT2",
            "version": "1.4",
            "Penetrance": "Complete"
        },
        {
            "SpecificDiseaseName": "Regional overgrowth disorders",
            "Publications": null,
            "Phenotypes": [
                "Hypoinsulinemic hypoglycemia with hemihypertrophy,240900",
                "Hypoinsulinemic hypoglycemia with hemihypertrophy",
                " HIHGHH",
                "Hypoinsulinemic hypoglycemia with hemihypertrophy, 240900"
            ],
            "EnsembleGeneIds": [
                "ENSG00000105221"
            ],
            "Evidences": [
                "Other",
                "Radboud University Medical Center, Nijmegen"
            ],
            "DiseaseGroup": "",
            "ModeOfInheritance": "monoallelic",
            "DiseaseSubGroup": "",
            "LevelOfConfidence": "LowEvidence",
            "ModeOfPathogenicity": null,
            "GeneSymbol": "AKT2",
            "version": "1.3",
            "Penetrance": "Complete"
        }
    ],
    "meta": {
        "numOfResults": 3
    }
}
```


## Filtering

Parameters:

- ModeOfInheritance: comma separated list of modes of inheritance, one of the following values:

    - `monoallelic_not_imprinted`
    - `monoallelic_maternally_imprinted`
    - `monoallelic_paternally_imprinted`
    - `monoallelic`
    - `biallelic`
    - `monoallelic_and_biallelic`
    - `monoallelic_and_more_severe_biallelic`
    - `xlinked_biallelic`
    - `xlinked_monoallelic`
    - `mitochondrial`
    - `unknown`

- `ModeOfPathogenicity`: comma separated list of modes of pathogenicities, one of the following values:

    - `loss_of_function`
    - `other`

- `Penetrance`: comma separated list of penetrance values, one of the following:

    - `unknown`
    - `Complete`
    - `Incomplete`

- `LevelOfConfidence`: comma separated list of confidence levels, one of the following:

    - `HighEvidence`
    - `ModerateEvidence`
    - `LowEvidence`

- `Evidences`: comma separated list of evidences, one of the following:

    - `radboud_university_medical_center_nijmegen`
    - `illumina_trugenome_clinical_sequencing_services`
    - `emory_genetics_laboratory`
    - `ukgtn`
    - `other`
    - `export_list`
    - `export_review`
    - `literature`
    - `eligibility_statement_prior_genetic_testing`
    - `research`

- `panel_name`: only search specified panel names, comma separated list

## Examples

- https://panelapp.genomicsengland.co.uk/WebServices/search_genes/AKT2/
- https://panelapp.genomicsengland.co.uk/WebServices/search_genes/AKT2/?ModeOfInheritance=biallelic,monoallelic
- https://panelapp.genomicsengland.co.uk/WebServices/search_genes/AKT2/?ModeOfPathogenicity=loss_of_function
- https://panelapp.genomicsengland.co.uk/WebServices/search_genes/AKT2/?Penetrance=Complete
- https://panelapp.genomicsengland.co.uk/WebServices/search_genes/AKT2/?LevelOfConfidence=HighEvidence,ModerateEvidence
- https://panelapp.genomicsengland.co.uk/WebServices/search_genes/AKT2/?Evidences=literature
- https://panelapp.genomicsengland.co.uk/WebServices/search_genes/AKT2/?panel_name=Regional%20overgrowth%20disorders

# Additional parameters

Additionally, you can specify `assembly` GET parameters with either `GRch37` (default) or `GRch38` as a value.

EnsemblIds will be returned for the specified assembly version: GRch37 version 82 or GRch38 version 90 if they exists in the database.

- https://panelapp.genomicsengland.co.uk/WebServices/search_genes/AKT2/?panel_name=Regional%20overgrowth%20disorders&assembly=GRch38