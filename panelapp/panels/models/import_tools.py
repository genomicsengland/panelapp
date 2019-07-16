##
## Copyright (c) 2016-2019 Genomics England Ltd.
##
## This file is part of PanelApp
## (see https://panelapp.genomicsengland.co.uk).
##
## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.
##
import json
import re
import csv
import logging
from datetime import datetime
from django.db import models
from django.db import transaction
from model_utils.models import TimeStampedModel
from accounts.models import User, Reviewer
from .genepanelentrysnapshot import GenePanelEntrySnapshot
from .strs import STR
from panels.tasks import import_panel
from panels.tasks import import_reviews
from panels.exceptions import TSVIncorrectFormat
from panels.exceptions import GeneDoesNotExist
from panels.exceptions import UsersDoNotExist
from panels.exceptions import GenesDoNotExist
from panels.exceptions import IncorrectGeneRating
from panels.exceptions import IsSuperPanelException
from .gene import Gene
from .genepanel import GenePanel
from .region import Region
from .genepanelsnapshot import GenePanelSnapshot
from .Level4Title import Level4Title
from .codes import ProcessingRunCode
from django.utils.encoding import force_text


logger = logging.getLogger(__name__)


def update_gene_collection(results):
    with transaction.atomic():
        to_insert = results["insert"]
        to_update = results["update"]
        to_update_gene_symbol = results["update_symbol"]
        to_delete = results["delete"]

        for p in GenePanelSnapshot.objects.get_active(
            all=True, internal=True, superpanels=False
        ):
            p = p.increment_version()

        for record in to_insert:
            new_gene = Gene.from_dict(record)
            if not new_gene.ensembl_genes:
                new_gene.active = False
            new_gene.save()
            logger.debug("Inserted {} gene".format(record["gene_symbol"]))

        to_insert = None
        results["insert"] = None

        try:
            user = User.objects.get(username="GEL")
        except User.DoesNotExist:
            user = User.objects.create(username="GEL", first_name="Genomics England")
            Reviewer.objects.create(
                user=user,
                user_type="GEL",
                affiliation="Genomics England",
                workplace="Other",
                role="Other",
                group="Other",
            )

        genes_in_panels = GenePanelEntrySnapshot.objects.get_active()
        grouped_genes = {gp.gene_core.gene_symbol: [] for gp in genes_in_panels}
        for gene_in_panel in genes_in_panels:
            grouped_genes[gene_in_panel.gene_core.gene_symbol].append(gene_in_panel)

        strs_in_panels = STR.objects.get_active()
        grouped_strs = {
            gp.gene_core.gene_symbol: [] for gp in strs_in_panels if gp.gene_core
        }
        for str_in_panel in strs_in_panels:
            grouped_strs[str_in_panel.gene_core.gene_symbol].append(str_in_panel)

        regions_in_panels = Region.objects.get_active()
        grouped_regions = {
            gp.gene_core.gene_symbol: [] for gp in regions_in_panels if gp.gene_core
        }
        for region_in_panel in regions_in_panels:
            grouped_regions[region_in_panel.gene_core.gene_symbol].append(
                region_in_panel
            )

        for record in to_update:
            try:
                gene = Gene.objects.get(gene_symbol=record["gene_symbol"])
            except Gene.DoesNotExist:
                gene = Gene(gene_symbol=record["gene_symbol"])

            gene.gene_name = record.get("gene_name", None)
            gene.ensembl_genes = record.get("ensembl_genes", {})
            gene.omim_gene = record.get("omim_gene", [])
            gene.alias = record.get("alias", [])
            gene.biotype = record.get("biotype", "unknown")
            gene.alias_name = record.get("alias_name", [])
            gene.hgnc_symbol = record["hgnc_symbol"]
            gene.hgnc_date_symbol_changed = record.get("hgnc_date_symbol_changed", None)
            gene.hgnc_release = record.get("hgnc_release", None)
            gene.hgnc_id = record.get("hgnc_id", None)
            if not gene.ensembl_genes:
                gene.active = False

            gene.clean_import_dates(record)

            gene.save()

            for gene_entry in grouped_genes.get(record["gene_symbol"], []):
                gene_entry.gene_core = gene
                gene_entry.gene = gene.dict_tr()
                gene_entry.save()

            for str_entry in grouped_strs.get(record["gene_symbol"], []):
                str_entry.gene_core = gene
                str_entry.gene = gene.dict_tr()
                str_entry.save()

            for region_entry in grouped_regions.get(record["gene_symbol"], []):
                region_entry.gene_core = gene
                region_entry.gene = gene.dict_tr()
                region_entry.save()

            logger.debug("Updated {} gene".format(record["gene_symbol"]))

        grouped_genes = None
        to_update = None
        results["update"] = None

        for record in to_update_gene_symbol:
            active = True
            ensembl_genes = record[0].get("ensembl_genes", {})
            if not ensembl_genes:
                active = False

            # some dates are in the wrong format: %d-%m-%y, Django expects %Y-%m-%-d
            hgnc_date_symbol_changed = record[0].get("hgnc_date_symbol_changed", "")
            if hgnc_date_symbol_changed and len(hgnc_date_symbol_changed) == 8:
                record[0]["hgnc_date_symbol_changed"] = datetime.strptime(
                    hgnc_date_symbol_changed, "%d-%m-%y"
                )

            if (
                record[0].get("hgnc_release", "")
                and len(record[0].get("hgnc_release", "")) == 8
            ):
                record[0]["hgnc_release"] = datetime.strptime(
                    record[0]["hgnc_release"], "%d-%m-%y"
                )

            try:
                new_gene = Gene.objects.get(gene_symbol=record[0]["gene_symbol"])
            except Gene.DoesNotExist:
                new_gene = Gene()

            # check if record has ensembl genes data if it doesn't and gene has
            # it - keep it as it is and mark gene as active
            if new_gene.pk:
                if not new_gene.ensembl_genes:
                    new_gene.active = active
                    new_gene.ensembl_genes = ensembl_genes
                else:
                    if not ensembl_genes:
                        new_gene.active = True
            else:
                new_gene.active = active
                new_gene.ensembl_genes = ensembl_genes

            new_gene.gene_symbol = record[0]["gene_symbol"]
            new_gene.gene_name = record[0].get("gene_name", None)
            new_gene.omim_gene = record[0].get("omim_gene", [])
            new_gene.alias = record[0].get("alias", [])
            new_gene.biotype = record[0].get("biotype", "unknown")
            new_gene.alias_name = record[0].get("alias_name", [])
            new_gene.hgnc_symbol = record[0]["hgnc_symbol"]
            new_gene.hgnc_date_symbol_changed = record[0].get(
                "hgnc_date_symbol_changed", None
            )
            new_gene.hgnc_release = record[0].get("hgnc_release", None)
            new_gene.hgnc_id = record[0].get("hgnc_id", None)

            new_gene.clean_import_dates(record[0])
            new_gene.save()

            for gene_entry in GenePanelEntrySnapshot.objects.get_active().filter(
                gene_core__gene_symbol=record[1]
            ):
                panel = gene_entry.panel
                panel.update_gene(user, record[1], {"gene": new_gene})

            for str_entry in STR.objects.get_active().filter(
                gene_core__gene_symbol=record[1]
            ):
                panel = str_entry.panel
                panel.update_str(user, str_entry.name, {"gene": new_gene})

            for region_entry in Region.objects.get_active().filter(
                gene_core__gene_symbol=record[1]
            ):
                panel = region_entry.panel
                panel.update_region(user, region_entry.name, {"gene": new_gene})

            try:
                d = Gene.objects.get(gene_symbol=record[1])
                d.active = False
                d.save()
                logger.debug(
                    "Updated {} gene. Renamed to {}".format(
                        record[1], record[0]["gene_symbol"]
                    )
                )
            except Gene.DoesNotExist:
                logger.debug(
                    "Created {} gene. Old gene {} didn't exist".format(
                        record[0]["gene_symbol"], record[1]
                    )
                )

        for record in to_delete:
            gene_in_panels = GenePanelEntrySnapshot.objects.get_active().filter(
                gene_core__gene_symbol=record
            )
            if gene_in_panels.count() > 0:
                distinct_panels = gene_in_panels.distinct().values_list(
                    "panel__panel__name", flat=True
                )
                logger.warning(
                    "Deleted {} gene, this one is still used in {}".format(
                        record, distinct_panels
                    )
                )

            strs_in_panels = STR.objects.get_active().filter(
                gene_core__gene_symbol=record
            )
            if strs_in_panels.count() > 0:
                distinct_panels = strs_in_panels.distinct().values_list(
                    "panel__panel__name", flat=True
                )
                logger.warning(
                    "Deleted {} gene, this one is still used in {}".format(
                        record, distinct_panels
                    )
                )

            regions_in_panels = Region.objects.get_active().filter(
                gene_core__gene_symbol=record
            )
            if regions_in_panels.count() > 0:
                distinct_panels = regions_in_panels.distinct().values_list(
                    "panel__panel__name", flat=True
                )
                logger.warning(
                    "Deleted {} gene, this one is still used in {}".format(
                        record, distinct_panels
                    )
                )

            try:
                old_gene = Gene.objects.get(gene_symbol=record)
                old_gene.active = False
                old_gene.save()
                logger.debug("Deleted {} gene".format(record))
            except Gene.DoesNotExist:
                logger.debug("Didn't delete {} gene - doesn't exist".format(record))

        duplicated_genes = get_duplicated_genes_in_panels()
        if duplicated_genes:
            logger.info("duplicated genes:")
            for g in duplicated_genes:
                logger.info(g)
                print(g)


def get_duplicated_genes_in_panels():
    duplicated_genes = []
    items = GenePanelSnapshot.objects.get_active_annotated(True)
    for item in items:
        dups = item.current_genes_duplicates
        if dups:
            duplicated_genes.append((item.pk, item.panel.name, dups))
    return duplicated_genes


class UploadedGeneList(TimeStampedModel):
    imported = models.BooleanField(default=False)
    gene_list = models.FileField(upload_to="genes", max_length=255)

    def create_genes(self):
        with open(self.gene_list.path) as file:
            logger.info("Started importing list of genes")
            results = json.load(file)
            update_gene_collection(results)

            self.imported = True
            self.save()


class UploadedPanelList(TimeStampedModel):
    imported = models.BooleanField(default=False)
    panel_list = models.FileField(upload_to="panels", max_length=255)
    import_log = models.TextField(default="")

    _map_tsv_to_kw = [
        {"name": "entity_name", "type": str},
        {
            "name": "entity_type",
            "type": str,
            "modifiers": [
                lambda value: value.lower() if isinstance(value, str) else value
            ],
        },
        {
            "name": "gene_symbol",
            "type": str,
            "modifiers": [lambda value: re.sub("[^0-9a-zA-Z~#_@-]", "", value)],
        },
        {"name": "sources", "type": "unique-list"},
        {"name": "level4", "type": str},
        {"name": "level3", "type": str},
        {"name": "level2", "type": str},
        {"name": "moi", "type": str},
        {"name": "phenotypes", "type": "unique-list"},
        {"name": "omim", "type": "unique-list"},
        {"name": "oprahanet", "type": "unique-list"},
        {"name": "hpo", "type": "unique-list"},
        {"name": "publications", "type": "unique-list"},
        {"name": "description", "type": "str"},
        {"name": "flagged", "type": "boolean"},
        {"name": "gel_status", "ignore": True},
        {"name": "user_ratings", "ignore": True},
        {"name": "version", "ignore": True},
        {"name": "ready", "ignore": True},
        {"name": "mode_of_pathogenicity", "type": str},
        {"name": "EnsemblId(GRch37)", "ignore": True},
        {"name": "EnsemblId(GRch38)", "ignore": True},
        {"name": "HGNC", "ignore": True},
        {"name": "chromosome", "type": str},
        {"name": "position_37_start", "type": int},
        {"name": "position_37_end", "type": int},
        {"name": "position_38_start", "type": int},
        {"name": "position_38_end", "type": int},
        {"name": "repeated_sequence", "type": str},
        {"name": "normal_repeats", "type": int},
        {"name": "pathogenic_repeats", "type": int},
        {"name": "haploinsufficiency_score", "type": str},
        {"name": "triplosensitivity_score", "type": str},
        {"name": "required_overlap_percentage", "type": int},
        {"name": "type_of_variants", "type": str},
        {"name": "verbose_name", "type": str},
    ]

    _required_line_length = {"gene": 15, "str": 31, "region": 35}

    _map_type_to_methods = {
        "gene": {
            "check_exists": "has_gene",
            "add": "add_gene",
            "update": "update_gene",
            "clear": [
                "cached_genes",
                "current_genes_count",
                "current_genes_duplicates",
                "current_genes",
                "get_all_genes",
                "get_all_genes_extra",
            ],
        },
        "str": {
            "check_exists": "has_str",
            "add": "add_str",
            "update": "update_str",
            "clear": ["cached_strs", "get_all_strs", "get_all_strs_extra"],
        },
        "region": {
            "check_exists": "has_region",
            "add": "add_region",
            "update": "update_region",
            "clear": ["cached_regions", "get_all_regions", "get_all_regions_extra"],
        },
    }

    _cached_panels = {}

    def get_entity_data(self, key, line, suppress_errors=False):
        """Translate TSV line to the dictionary values

        Also convert it into the correct types, check if we have all data
        for each type, and do some processing depending on the data
        type.

        :param key: TSV line number
        :param line: TSV line data
        :return: dict
        """
        entity_data = {}

        try:
            for index, item in enumerate(line):
                item_mapping = self._map_tsv_to_kw[index]

                if item_mapping.get("ignore", False):
                    item = None
                elif item_mapping["type"] == "boolean":
                    item = item.lower() == "true"
                elif item_mapping["type"] in [str, int]:
                    if item == "":
                        item = ""
                    else:
                        item = item_mapping["type"](item)
                        for modifier in item_mapping.get("modifiers", []):
                            item = modifier(item)
                elif item_mapping["type"] == "unique-list":
                    item = list(set([i.strip() for i in item.split(";") if i.strip()]))

                entity_data[item_mapping["name"]] = item
        except (IndexError, ValueError) as e:
            logger.exception(e, exc_info=True)
            if not suppress_errors:
                raise TSVIncorrectFormat(str(key + 2))

        if entity_data.get("entity_type", "") not in ["gene", "region", "str"]:
            logger.error(
                "TSV Import. Line: {} Incorrect entity type: {}".format(
                    str(key + 2), entity_data.get("entity_type")
                )
            )
            if not suppress_errors:
                raise TSVIncorrectFormat(str(key + 2))

        if (
            len(entity_data.keys())
            < self._required_line_length[entity_data["entity_type"]]
        ):
            logger.error(
                "TSV Import. Line: {} Incorrect line length: {}".format(
                    str(key + 2), len(entity_data.keys())
                )
            )
            if not suppress_errors:
                raise TSVIncorrectFormat(str(key + 2))

        if entity_data["entity_type"] in ["str", "region"]:
            if entity_data["position_37_start"] and entity_data["position_37_end"]:
                if entity_data["position_37_start"] >= entity_data["position_37_end"]:
                    logger.error(
                        "TSV Import. Line: {} Incorrect Post 37: {}".format(
                            str(key + 2), len(entity_data.keys())
                        )
                    )
                    if not suppress_errors:
                        raise TSVIncorrectFormat(str(key + 2))

                entity_data["position_37"] = [
                    entity_data["position_37_start"],
                    entity_data["position_37_end"],
                ]
            else:
                entity_data["position_37"] = None

            if (
                not entity_data["position_38_start"]
                or not entity_data["position_38_end"]
            ):
                logger.error(
                    "TSV Import. Line: {} Incorrect Post 38: {}".format(
                        str(key + 2), len(entity_data.keys())
                    )
                )

                if not suppress_errors:
                    raise TSVIncorrectFormat(str(key + 2))
            elif entity_data["position_38_start"] >= entity_data["position_38_end"]:
                logger.error(
                    "TSV Import. Line: {} Incorrect Post 38: {}".format(
                        str(key + 2), len(entity_data.keys())
                    )
                )
                if not suppress_errors:
                    raise TSVIncorrectFormat(str(key + 2))

            entity_data["position_38"] = [
                entity_data["position_38_start"],
                entity_data["position_38_end"],
            ]
        entity_data["name"] = entity_data["entity_name"]

        return entity_data

    def process_line(self, key, line, user):
        entity_data = self.get_entity_data(key, line)

        panel = self.get_panel(entity_data)

        # Add or update entity
        methods = self._map_type_to_methods[entity_data["entity_type"]]

        if entity_data["entity_type"] == "gene" or entity_data["gene_symbol"]:
            # Check if we want to add a gene which doesn't exist in our database
            try:
                entity_data["gene"] = Gene.objects.get(
                    gene_symbol=entity_data["gene_symbol"], active=True
                )
            except Gene.DoesNotExist:
                raise GeneDoesNotExist(
                    "{}, Gene: {}".format(key + 2, entity_data["gene_symbol"])
                )

        if not getattr(panel, methods["check_exists"])(entity_data["entity_name"]):
            getattr(panel, methods["add"])(
                user, entity_data["entity_name"], entity_data, False
            )
        else:
            getattr(panel, methods["update"])(
                user, entity_data["entity_name"], entity_data, True
            )

        getattr(panel, "clear_cache")(methods["clear"])

    def get_panel(self, line_data):
        return self._cached_panels[line_data["level4"]]

    def process_file(self, user, background=False):
        """Process uploaded file

        If the file has too many lines it wil run the import in the background.abs

        returns ProcessingRunCode
        """
        with self.panel_list.open(mode="rt") as file:
            # When file is stored in S3 we need to read the file returned by FieldFile.open(), then force it into text
            # and split the content into lines
            # TODO is this working when using FileSystemStorage?
            textfile_content = force_text(file.read(), encoding="utf-8",errors="ignore")
            reader = csv.reader(textfile_content.splitlines(), delimiter="\t")
            _ = next(reader)  # noqa

            lines = [line for line in reader]

            unique_panels = {l[4]: i for i, l in enumerate(lines)}

            errors = {"invalid_genes": [], "invalid_lines": []}

            if not background and len(lines) > 200:
                import_panel.delay(user.pk, self.pk)
                return ProcessingRunCode.PROCESS_BACKGROUND

            with transaction.atomic():
                # check the number of genes in a panel
                for panel_name, index in unique_panels.items():
                    gp = GenePanel.objects.filter(name=panel_name).first()
                    if gp:
                        if gp.active_panel.is_super_panel:
                            raise IsSuperPanelException
                        else:
                            number_of_entities = gp.active_panel.stats.get(
                                "number_of_entities", 0
                            )

                            if not background and number_of_entities > 200:
                                # panel is too big, process in the background
                                import_panel.delay(user.pk, self.pk)
                                return ProcessingRunCode.PROCESS_BACKGROUND

                            self._cached_panels[
                                panel_name
                            ] = gp.active_panel.increment_version()
                    else:
                        line_data = self.get_entity_data(
                            index, lines[index], suppress_errors=True
                        )
                        level4_object = Level4Title.objects.create(
                            level2title=line_data["level2"],
                            level3title=line_data["level3"],
                            name=line_data["level4"],
                            description=line_data["description"],
                            omim=line_data["omim"],
                            hpo=line_data["hpo"],
                            orphanet=line_data["oprahanet"],
                        )
                        panel = GenePanel.objects.create(name=line_data["level4"])
                        active_panel = GenePanelSnapshot.objects.create(
                            panel=panel, level4title=level4_object, old_panels=[]
                        )
                        panel.add_activity(user, "Added panel {}".format(panel.name))
                        self._cached_panels[line_data["level4"]] = active_panel

                for key, line in enumerate(lines):
                    try:
                        self.process_line(key + 1, line, user)
                    except GeneDoesNotExist as gene_error:
                        errors["invalid_genes"].append(str(gene_error))
                    except TSVIncorrectFormat as line_error:
                        errors["invalid_lines"].append(str(line_error))

                if errors["invalid_genes"]:
                    raise GenesDoNotExist(", ".join(errors["invalid_genes"]))

                if errors["invalid_lines"]:
                    raise TSVIncorrectFormat(", ".join(errors["invalid_lines"]))

            self.imported = True
            self.save()

        return ProcessingRunCode.PROCESSED


class UploadedReviewsList(TimeStampedModel):
    """Review files uploaded by the curation team"""

    imported = models.BooleanField(default=False)
    reviews = models.FileField(upload_to="reviews", max_length=255)
    import_log = models.TextField(default="")

    panels = {}
    database_users = {}

    def process_line(self, key, line):
        """Process individual line"""

        aline = line
        if len(aline) < 21:
            raise TSVIncorrectFormat(str(key + 2))

        gene_symbol = re.sub(
            "[^0-9a-zA-Z~#_@-]", "", aline[0]
        )  # TODO (Oleg) should be unified (in settings?)
        # source = aline[1].split(";")
        level4 = aline[2].rstrip(" ")
        # level3 = aline[3]
        # level2 = aline[4]
        model_of_inheritance = aline[5]
        phenotype = [ph for ph in aline[6].split(";") if ph]
        # omim = aline[7].split(";")
        # oprahanet = aline[8].split(";")
        # hpo = aline[9].split(";")
        publication = [pub for pub in aline[10].split(";") if pub]
        # description = aline[11] # ? What description

        mop = aline[17]
        rate = aline[18]

        panelapp_ratings = {
            "Green List (high evidence)": "GREEN",
            "Red List (low evidence)": "RED",
            "I don't know": "AMBER",
        }

        if (
            rate not in panelapp_ratings.values()
            and rate not in panelapp_ratings.keys()
        ):
            raise IncorrectGeneRating(
                "Line: {} has incorrect Gene rating: {}".format(key + 2, rate)
            )

        if rate not in panelapp_ratings.values():
            rate = panelapp_ratings[rate]

        current_diagnostic = aline[19]
        if current_diagnostic == "Yes":
            current_diagnostic = True
        else:
            current_diagnostic = False
        comments = aline[20]
        username = aline[21]

        active_panel = self.panels.get(level4)
        if active_panel:
            if not active_panel.has_gene(gene_symbol):
                raise GeneDoesNotExist("Line: {} Gene: {}".format(key + 2, gene_symbol))

            gene = active_panel.get_gene(gene_symbol)

            evaluation_data = {
                "comment": comments,
                "mode_of_pathogenicity": mop,
                "phenotypes": phenotype,
                "moi": model_of_inheritance,
                "current_diagnostic": current_diagnostic,
                "rating": rate,
                "publications": publication,
            }
            user = self.database_users.get(username)
            gene.update_evaluation(user, evaluation_data)

    def process_file(self, user, background=False):
        """Process uploaded file.

        If file has more than 200 lines process it in the background.

        Returns ProcessingRunCode
        """
        with self.reviews.open(mode="rt") as file:
            # TODO is this working when using FileSystemStorage?
            textfile_content = force_text(file.read(), encoding="utf-8",errors="ignore")
            reader = csv.reader(textfile_content.splitlines(), delimiter="\t")
            next(reader)  # skip header

            with transaction.atomic():
                lines = [line for line in reader]
                users = set([line[21] for line in lines])

                self.database_users = {
                    u.username: u for u in User.objects.filter(username__in=users)
                }
                non_existing_users = users.symmetric_difference(
                    self.database_users.keys()
                )
                if len(non_existing_users) > 0:
                    raise UsersDoNotExist(", ".join(non_existing_users))

                # TODO (Oleg) replace with a constant
                genes = set(
                    [re.sub("[^0-9a-zA-Z~#_@-]", "", line[0]) for line in lines]
                )
                database_genes = Gene.objects.filter(gene_symbol__in=genes).values_list(
                    "gene_symbol", flat=True
                )
                non_existing_genes = genes.symmetric_difference(database_genes)
                if len(non_existing_genes) > 0:
                    raise GenesDoNotExist(", ".join(non_existing_genes))

                if (
                    not background and len(lines) > 50
                ):  # panel is too big, process in the background
                    import_reviews.delay(user.pk, self.pk)
                    return ProcessingRunCode.PROCESS_BACKGROUND

                panel_names = set([line[2] for line in lines])
                self.panels = {
                    panel.name: panel.active_panel
                    for panel in GenePanel.objects.filter(name__in=panel_names)
                }
                for active_panel in list(self.panels.values()):
                    if active_panel.is_super_panel:
                        raise IsSuperPanelException
                    self.panels[
                        active_panel.panel.name
                    ] = active_panel.increment_version()

                errors = {"invalid_genes": [], "invalid_lines": []}

                for key, line in enumerate(lines):
                    try:
                        self.process_line(key, line)
                    except GeneDoesNotExist as gene_error:
                        errors["invalid_genes"].append(str(gene_error))
                    except TSVIncorrectFormat as line_error:
                        errors["invalid_lines"].append(str(line_error))

                if errors["invalid_genes"]:
                    raise GenesDoNotExist(", ".join(errors["invalid_genes"]))

                if errors["invalid_lines"]:
                    raise TSVIncorrectFormat(", ".join(errors["invalid_lines"]))

                self.imported = True
                self.save()
                return ProcessingRunCode.PROCESSED
