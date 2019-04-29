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
import csv
from datetime import datetime

from django.contrib import messages
from django.views.generic.base import View
from django.views.generic import FormView
from django.views.generic import DetailView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.template.defaultfilters import pluralize
from django.http import HttpResponse
from django.http import StreamingHttpResponse

from panelapp.mixins import GELReviewerRequiredMixin
from panels.forms import ComparePanelsForm
from panels.forms import CopyReviewsForm

from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.models import ProcessingRunCode
from panels.models import HistoricalSnapshot
from panels.mixins import PanelMixin
from panels.utils import remove_non_ascii
from .entities import EchoWriter


class DownloadPanelTSVMixin(PanelMixin, DetailView):
    model = GenePanelSnapshot

    def get(self, *args, **kwargs):
        return self.process()

    def process(self):
        self.object = self.get_object()

        panel_name = self.object.panel.name
        version = self.object.version

        response = HttpResponse(content_type="text/tab-separated-values")
        panel_name = remove_non_ascii(panel_name, replacemenet="_")
        response["Content-Disposition"] = (
            'attachment; filename="' + panel_name + '.tsv"'
        )
        writer = csv.writer(response, delimiter="\t")

        writer.writerow(
            (
                "Entity Name",
                "Entity type",
                "Gene Symbol",
                "Sources(; separated)",
                "Level4",
                "Level3",
                "Level2",
                "Model_Of_Inheritance",
                "Phenotypes",
                "Omim",
                "Orphanet",
                "HPO",
                "Publications",
                "Description",
                "Flagged",
                "GEL_Status",
                "UserRatings_Green_amber_red",
                "version",
                "ready",
                "Mode of pathogenicity",
                "EnsemblId(GRch37)",
                "EnsemblId(GRch38)",
                "HGNC",
                "Position Chromosome",
                "Position GRCh37 Start",
                "Position GRCh37 End",
                "Position GRCh38 Start",
                "Position GRCh38 End",
                "STR Repeated Sequence",
                "STR Normal Repeats",
                "STR Pathogenic Repeats",
                "Region Haploinsufficiency Score",
                "Region Triplosensitivity Score",
                "Region Required Overlap Percentage",
                "Region Variant Type",
                "Region Verbose Name",
            )
        )

        categories = self.get_categories()
        for gpentry in self.object.get_all_genes_extra:
            if (
                not gpentry.flagged
                and gpentry.saved_gel_status > 0
                and str(gpentry.status) in categories
            ):
                amber_perc, green_perc, red_prec = gpentry.aggregate_ratings()

                ensembl_id_37 = "-"
                try:
                    ensembl_id_37 = (
                        gpentry.gene.get("ensembl_genes", {})
                        .get("GRch37", {})
                        .get("82", {})
                        .get("ensembl_id", "-")
                    )
                except AttributeError:
                    pass

                ensembl_id_38 = "-"
                try:
                    ensembl_id_38 = (
                        gpentry.gene.get("ensembl_genes", {})
                        .get("GRch38", {})
                        .get("90", {})
                        .get("ensembl_id", "-")
                    )
                except AttributeError:
                    pass

                evidence = ";".join([ev for ev in gpentry.entity_evidences if ev])
                export_gpentry = (
                    gpentry.gene.get("gene_symbol"),
                    "gene",
                    gpentry.gene.get("gene_symbol"),
                    evidence,
                    panel_name,
                    self.object.level4title.level3title,
                    self.object.level4title.level2title,
                    gpentry.moi,
                    ";".join(map(remove_non_ascii, gpentry.phenotypes)),
                    ";".join(map(remove_non_ascii, self.object.level4title.omim)),
                    ";".join(map(remove_non_ascii, self.object.level4title.orphanet)),
                    ";".join(map(remove_non_ascii, self.object.level4title.hpo)),
                    ";".join(map(remove_non_ascii, gpentry.publications))
                    if gpentry.publications
                    else "",
                    "",
                    str(gpentry.flagged),
                    str(gpentry.saved_gel_status),
                    ";".join(map(str, [green_perc, amber_perc, red_prec])),
                    str(version),
                    gpentry.ready,
                    gpentry.mode_of_pathogenicity,
                    ensembl_id_37,
                    ensembl_id_38,
                    gpentry.gene.get("hgnc_id", "-"),
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                )
                writer.writerow(export_gpentry)

        for strentry in self.object.get_all_strs_extra:
            if (
                not strentry.flagged
                and strentry.saved_gel_status > 0
                and str(strentry.status) in categories
            ):
                amber_perc, green_perc, red_prec = strentry.aggregate_ratings()

                evidence = ";".join(
                    [evidence.name for evidence in strentry.evidence.all()]
                )
                export_strentry = (
                    strentry.name,
                    "str",
                    strentry.gene.get("gene_symbol") if strentry.gene else "",
                    evidence,
                    panel_name,
                    self.object.level4title.level3title,
                    self.object.level4title.level2title,
                    strentry.moi,
                    ";".join(map(remove_non_ascii, strentry.phenotypes)),
                    ";".join(map(remove_non_ascii, self.object.level4title.omim)),
                    ";".join(map(remove_non_ascii, self.object.level4title.orphanet)),
                    ";".join(map(remove_non_ascii, self.object.level4title.hpo)),
                    ";".join(map(remove_non_ascii, strentry.publications))
                    if strentry.publications
                    else "",
                    "",
                    str(strentry.flagged),
                    str(strentry.saved_gel_status),
                    ";".join(map(str, [green_perc, amber_perc, red_prec])),
                    str(version),
                    strentry.ready,
                    "",
                    strentry.gene.get("ensembl_genes", {})
                    .get("GRch37", {})
                    .get("82", {})
                    .get("ensembl_id", "-")
                    if strentry.gene
                    else "",
                    strentry.gene.get("ensembl_genes", {})
                    .get("GRch38", {})
                    .get("90", {})
                    .get("ensembl_id", "-")
                    if strentry.gene
                    else "",
                    strentry.gene.get("hgnc_id", "-") if strentry.gene else "",
                    strentry.chromosome,
                    strentry.position_37.lower if strentry.position_37 else "",
                    strentry.position_37.upper if strentry.position_37 else "",
                    strentry.position_38.lower,
                    strentry.position_38.upper,
                    strentry.repeated_sequence,
                    strentry.normal_repeats,
                    strentry.pathogenic_repeats,
                    "",
                    "",
                    "",
                    "",
                    "",
                )
                writer.writerow(export_strentry)

        for region in self.object.get_all_regions_extra:
            if (
                not region.flagged
                and region.saved_gel_status > 0
                and str(region.status) in categories
            ):
                amber_perc, green_perc, red_prec = region.aggregate_ratings()

                evidence = ";".join(
                    [evidence.name for evidence in region.evidence.all()]
                )
                export_region = (
                    region.name,
                    "region",
                    region.gene.get("gene_symbol") if region.gene else "",
                    evidence,
                    panel_name,
                    self.object.level4title.level3title,
                    self.object.level4title.level2title,
                    region.moi,
                    ";".join(map(remove_non_ascii, region.phenotypes)),
                    ";".join(map(remove_non_ascii, self.object.level4title.omim)),
                    ";".join(map(remove_non_ascii, self.object.level4title.orphanet)),
                    ";".join(map(remove_non_ascii, self.object.level4title.hpo)),
                    ";".join(map(remove_non_ascii, region.publications))
                    if region.publications
                    else "",
                    "",
                    str(region.flagged),
                    str(region.saved_gel_status),
                    ";".join(map(str, [green_perc, amber_perc, red_prec])),
                    str(version),
                    region.ready,
                    "",
                    region.gene.get("ensembl_genes", {})
                    .get("GRch37", {})
                    .get("82", {})
                    .get("ensembl_id", "-")
                    if region.gene
                    else "",
                    region.gene.get("ensembl_genes", {})
                    .get("GRch38", {})
                    .get("90", {})
                    .get("ensembl_id", "-")
                    if region.gene
                    else "",
                    region.gene.get("hgnc_id", "-") if region.gene else "",
                    region.chromosome,
                    region.position_37.lower if region.position_37 else "",
                    region.position_37.upper if region.position_37 else "",
                    region.position_38.lower,
                    region.position_38.upper,
                    "",
                    "",
                    "",
                    region.haploinsufficiency_score,
                    region.triplosensitivity_score,
                    region.required_overlap_percentage,
                    region.type_of_variants,
                    region.verbose_name,
                )
                writer.writerow(export_region)

        return response


class DownloadPanelTSVView(DownloadPanelTSVMixin):
    def get_categories(self):
        return self.kwargs["categories"]


class DownloadPanelVersionTSVView(DownloadPanelTSVMixin):
    def get_categories(self):
        return "01234"

    def get_object(self):
        panel_version = self.request.POST.get("panel_version")
        panel = GenePanel.objects.get_active_panel(pk=self.kwargs["pk"])
        if panel_version:
            try:
                major_version, minor_version = panel_version.split(".")
            except ValueError:
                raise APIException(
                    detail="Incorrect version supplied", code="incorrect_version"
                )
            if major_version == str(panel.major_version) and minor_version == str(panel.minor_version):
                return panel

            snapshot = HistoricalSnapshot.objects.filter(panel__pk=self.kwargs["pk"],
                                                     major_version=major_version,
                                                     minor_version=minor_version).first()
            return snapshot
        else:
            return panel

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        if not self.object:
            msg = "Can't find panel with the version {}".format(
                self.request.POST.get("panel_version")
            )
            messages.error(self.request, msg)
            return redirect(
                reverse_lazy("panels:detail", kwargs={"pk": self.kwargs["pk"]})
            )
        elif isinstance(self.object, HistoricalSnapshot):
            return self.object.to_tsv()
        else:
            return self.process()


class ComparePanelsView(FormView):
    template_name = "panels/compare/compare_panels.html"
    form_class = ComparePanelsForm

    def form_valid(self, form):
        panel_1 = form.cleaned_data["panel_1"]
        panel_2 = form.cleaned_data["panel_2"]
        return redirect(
            reverse_lazy("panels:compare", args=(panel_1.panel.pk, panel_2.panel.pk))
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        is_admin = (
            True
            if self.request.user.is_authenticated
            and self.request.user.reviewer.is_GEL()
            else False
        )
        kwargs["panels"] = GenePanelSnapshot.objects.get_active(
            all=is_admin, internal=is_admin
        )

        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data()

        if self.kwargs.get("panel_1_id") and self.kwargs.get("panel_2_id"):
            ctx["panel_1"] = panel_1 = GenePanel.objects.get_panel(
                pk=self.kwargs["panel_1_id"]
            ).active_panel
            ctx["panel_2"] = panel_2 = GenePanel.objects.get_panel(
                pk=self.kwargs["panel_2_id"]
            ).active_panel

            panel_1_items = {
                e.gene.get("gene_symbol"): e for e in panel_1.get_all_genes_extra
            }
            panel_2_items = {
                e.gene.get("gene_symbol"): e for e in panel_2.get_all_genes_extra
            }

            all = list(set(panel_1_items.keys()) | set(panel_2_items.keys()))
            all.sort()

            intersection = list(set(panel_1_items.keys() & set(panel_2_items.keys())))
            ctx["show_copy_reviews"] = (
                self.request.user.is_authenticated
                and self.request.user.reviewer.is_GEL()
                and len(intersection) > 0
            )

            comparison = [
                [
                    gene,
                    panel_1_items[gene] if gene in panel_1_items else False,
                    panel_2_items[gene] if gene in panel_2_items else False,
                ]
                for gene in all
            ]

            ctx["comparison"] = comparison
        else:
            ctx["panel_1"] = None
            ctx["panel_2"] = None
            ctx["show_copy_reviews"] = None
            ctx["comparison"] = None

        return ctx


class CompareGeneView(FormView):
    template_name = "panels/compare/compare_genes.html"
    form_class = ComparePanelsForm

    def form_valid(self, form):
        panel_1 = form.cleaned_data["panel_1"]
        panel_2 = form.cleaned_data["panel_2"]
        args = (panel_1.panel.pk, panel_2.panel.pk, self.kwargs["gene_symbol"])
        return redirect(reverse_lazy("panels:compare_genes", args=args))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        is_admin = (
            True
            if self.request.user.is_authenticated
            and self.request.user.reviewer.is_GEL()
            else False
        )
        kwargs["panels"] = GenePanelSnapshot.objects.get_active(
            all=is_admin, internal=is_admin
        )

        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data()
        gene_symbol = self.kwargs["gene_symbol"]
        ctx["gene_symbol"] = gene_symbol

        ctx["panel_1"] = panel_1 = GenePanel.objects.get_panel(
            pk=self.kwargs["panel_1_id"]
        ).active_panel
        ctx["panel_2"] = panel_2 = GenePanel.objects.get_panel(
            pk=self.kwargs["panel_2_id"]
        ).active_panel
        ctx["panel_1_entry"] = panel_1.get_gene(gene_symbol, prefetch_extra=True)
        ctx["panel_2_entry"] = panel_2.get_gene(gene_symbol, prefetch_extra=True)

        return ctx


class CopyReviewsView(GELReviewerRequiredMixin, FormView):
    template_name = "panels/compare/copy_reviews.html"
    form_class = CopyReviewsForm

    def form_valid(self, form):
        ctx = self.get_context_data()
        process_type, total_count = form.copy_reviews(
            self.request.user.pk, ctx["intersection"], ctx["panel_1"], ctx["panel_2"]
        )

        if process_type == ProcessingRunCode.PROCESSED:
            messages.success(
                self.request,
                "{} review{} copied".format(total_count, pluralize(total_count)),
            )
        else:
            messages.error(
                self.request,
                "Panels have too many genes, reviews will be copied in the background.",
            )

        return redirect(
            reverse_lazy(
                "panels:compare",
                args=(ctx["panel_1"].panel.pk, ctx["panel_2"].panel.pk),
            )
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["initial"] = {
            "panel_1": GenePanel.objects.get_panel(
                pk=self.kwargs["panel_1_id"]
            ).active_panel.pk,
            "panel_2": GenePanel.objects.get_panel(
                pk=self.kwargs["panel_2_id"]
            ).active_panel.pk,
        }
        return kwargs

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)

        ctx["panel_1"] = panel_1 = GenePanel.objects.get_panel(
            pk=self.kwargs["panel_1_id"]
        ).active_panel
        ctx["panel_2"] = panel_2 = GenePanel.objects.get_panel(
            pk=self.kwargs["panel_2_id"]
        ).active_panel

        panel_1_items = {
            e.gene.get("gene_symbol"): e for e in panel_1.get_all_genes_extra
        }
        panel_2_items = {
            e.gene.get("gene_symbol"): e for e in panel_2.get_all_genes_extra
        }

        intersection = list(set(panel_1_items.keys() & set(panel_2_items.keys())))
        intersection.sort()
        ctx["intersection"] = intersection

        comparison = [
            [gene, panel_1_items[gene], panel_2_items[gene]] for gene in intersection
        ]
        ctx["comparison"] = comparison

        return ctx


class DownloadAllGenes(GELReviewerRequiredMixin, View):
    def gene_iterator(self):
        yield (
            "Symbol",
            "Panel Id",
            "Panel Name",
            "Panel Version",
            "Panel Status",
            "List",
            "Sources",
            "Mode of inheritance",
            "Mode of pathogenicity",
            "Tags",
            "EnsemblId(GRch37)",
            "EnsemblId(GRch38)",
            "HGNC",
            "Biotype",
            "Phenotypes",
            "GeneLocation((GRch37)",
            "GeneLocation((GRch38)",
            "Panel Types",
            "Super Panel Id",
            "Super Panel Name",
            "Super Panel Version",
        )

        for gps in GenePanelSnapshot.objects.get_active(
            all=True, internal=True
        ).iterator():
            is_super_panel = gps.is_super_panel
            super_panel_id = gps.panel_id
            super_panel_name = gps.level4title.name
            super_panel_version = gps.version

            for entry in gps.get_all_genes_extra:
                color = entry.entity_color_name

                if isinstance(entry.phenotypes, list):
                    phenotypes = ";".join(entry.phenotypes)
                else:
                    phenotypes = "-"

                ensembl_id_37 = "-"
                location_37 = "-"
                try:
                    ensembl_id_37 = (
                        entry.gene.get("ensembl_genes", {})
                        .get("GRch37", {})
                        .get("82", {})
                        .get("ensembl_id", "-")
                    )
                    location_37 = (
                        entry.gene.get("ensembl_genes", {})
                        .get("GRch37", {})
                        .get("82", {})
                        .get("location", "-")
                    )
                except AttributeError:
                    pass

                ensembl_id_38 = "-"
                location_38 = "-"
                try:
                    ensembl_id_38 = (
                        entry.gene.get("ensembl_genes", {})
                        .get("GRch38", {})
                        .get("90", {})
                        .get("ensembl_id", "-")
                    )
                    location_38 = (
                        entry.gene.get("ensembl_genes", {})
                        .get("GRch38", {})
                        .get("90", {})
                        .get("location", "-")
                    )
                except AttributeError:
                    pass

                row = [
                    entry.gene.get("gene_symbol"),
                    entry.panel.panel.pk,
                    entry.panel.level4title.name,
                    entry.panel.version,
                    str(entry.panel.panel.status).upper(),
                    color,
                    ";".join([ev for ev in entry.entity_evidences if ev]),
                    entry.moi,
                    entry.mode_of_pathogenicity,
                    ";".join([tag for tag in entry.entity_tags if tag]),
                    ensembl_id_37,
                    ensembl_id_38,
                    entry.gene.get("hgnc_id", "-"),
                    entry.gene.get("biotype", "-"),
                    phenotypes,
                    location_37,
                    location_38,
                    ";".join([t.name for t in entry.panel.panel.types.all()]),
                    super_panel_id if is_super_panel else "-",
                    super_panel_name if is_super_panel else "-",
                    super_panel_version if is_super_panel else "-",
                ]
                yield row

    def get(self, request, *args, **kwargs):
        pseudo_buffer = EchoWriter()
        writer = csv.writer(pseudo_buffer, delimiter="\t")

        response = StreamingHttpResponse(
            (writer.writerow(row) for row in self.gene_iterator()),
            content_type="text/tab-separated-values",
        )
        attachment = "attachment; filename=All_genes_{}.tsv".format(
            datetime.now().strftime("%Y%m%d-%H%M")
        )
        response["Content-Disposition"] = attachment
        return response
