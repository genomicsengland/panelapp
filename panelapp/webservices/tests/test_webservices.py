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
from django.test import TransactionTestCase
from django.urls import reverse_lazy
from panels.models import GenePanel
from panels.models import PanelType
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import STRFactory
from panels.tests.factories import RegionFactory
from panels.tests.factories import PanelTypeFactory
from webservices.utils import convert_mop


class TestWebservices(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.gps = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        self.gps_public = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        self.gpes = GenePanelEntrySnapshotFactory(panel=self.gps_public)
        self.gpes_internal = GenePanelEntrySnapshotFactory(panel__panel__status=GenePanel.STATUS.internal)
        self.gpes_retired = GenePanelEntrySnapshotFactory(panel__panel__status=GenePanel.STATUS.retired)
        self.gpes_deleted = GenePanelEntrySnapshotFactory(panel__panel__status=GenePanel.STATUS.deleted)
        self.genes = GenePanelEntrySnapshotFactory.create_batch(4, panel=self.gps)
        self.str = STRFactory(panel__panel__status=GenePanel.STATUS.public)
        self.region = RegionFactory(panel__panel__status=GenePanel.STATUS.public)
        self.region2 = RegionFactory(panel__panel__status=GenePanel.STATUS.public, position_37=None)

    def test_list_panels(self):
        r = self.client.get(reverse_lazy('webservices:list_panels'))
        self.assertEqual(r.status_code, 200)

    def test_list_panels_name(self):
        url = reverse_lazy('webservices:list_panels')
        r = self.client.get("{}?Types=all".format(url))
        self.assertEqual(len(r.json()['result']), 5)
        self.assertEqual(r.status_code, 200)

    def test_list_100k_rd_type(self):
        panel_type, _ = PanelType.objects.get_or_create(name='rare-disease-100k')
        self.gps.panel.types.add(panel_type)
        url = reverse_lazy('webservices:list_panels')
        r = self.client.get(url)
        self.assertEqual(len(r.json()['result']), 1)
        self.assertEqual(r.status_code, 200)

    def test_list_panels_filter_type(self):
        panel_type = PanelTypeFactory()
        self.gps.panel.types.add(panel_type)
        url = reverse_lazy('webservices:list_panels')
        r = self.client.get(url + '?Types=' + panel_type.slug)
        self.assertEqual(len(r.json()['result']), 1)
        self.assertEqual(r.json()['result'][0]['Name'], self.gps.panel.name)
        self.assertEqual(r.status_code, 200)

    def test_retired_panels(self):
        url = reverse_lazy('webservices:list_panels')

        self.gps.panel.status = GenePanel.STATUS.deleted
        self.gps.panel.save()

        r = self.client.get("{}?Types=all".format(url))
        self.assertEqual(len(r.json()['result']), 4)
        self.assertEqual(r.status_code, 200)

        # Test deleted panels
        url = reverse_lazy('webservices:list_panels')
        r = self.client.get("{}?Retired=True&Types=all".format(url))
        self.assertEqual(len(r.json()['result']), 5)  # one for gpes via factory, 2nd - retired
        self.assertEqual(r.status_code, 200)

        # Test for unapproved panels
        self.gps_public.panel.status = GenePanel.STATUS.internal
        self.gps_public.panel.save()

        url = reverse_lazy('webservices:list_panels')
        r = self.client.get("{}?Retired=True&Types=all".format(url))
        self.assertEqual(len(r.json()['result']), 4)  # only retired panel will be visible
        self.assertEqual(r.status_code, 200)

    def test_internal_panel(self):
        self.gps.panel.status = GenePanel.STATUS.internal
        self.gps.panel.save()
        url = reverse_lazy('webservices:get_panel', args=(self.gps.panel.pk, ))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), ["Query Error: {} not found.".format(self.gps.panel.pk)])

        self.gps.panel.active_panel.increment_version()
        del self.gps.panel.active_panel
        self.gps.panel.active_panel.increment_version()
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)
        self.assertIsNot(type(r.json()), list)
        self.assertIsNotNone(r.json().get('result'))

    def test_get_panel_name(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gpes.panel.panel.name,)))
        self.assertEqual(r.status_code, 200)

    def test_get_panel_name_deleted(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gpes_deleted.panel.panel.name,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), ["Query Error: {} not found.".format(self.gpes_deleted.panel.panel.name)])

    def test_get_panel_internal(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gpes_internal.panel.panel.name,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), ["Query Error: {} not found.".format(self.gpes_internal.panel.panel.name)])

    def test_get_panel_retired(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gpes_retired.panel.panel.name,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), ["Query Error: {} not found.".format(self.gpes_retired.panel.panel.name)])

    def test_get_panel_pk(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gpes.panel.panel.pk,)))
        self.assertEqual(r.status_code, 200)

    def test_get_panel_version(self):
        self.gpes.panel.increment_version()
        del self.gpes.panel.panel.active_panel
        self.gpes.panel.panel.active_panel.increment_version()

        url = reverse_lazy('webservices:get_panel', args=(self.gpes.panel.panel.pk,))
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)

        self.gps.panel.status = GenePanel.STATUS.retired
        self.gps.panel.save()

        url = reverse_lazy('webservices:get_panel', args=(self.gpes.panel.panel.pk,))
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(b'Query Error' not in r.content)

    def test_panel_created_timestamp(self):
        self.gpes.panel.increment_version()
        url = reverse_lazy('webservices:list_panels')
        res = self.client.get("{}?Types=all".format(url))
        # find gps panel
        title = self.gps_public.panel.name
        current_time = str(self.gps_public.created).replace('+00:00', 'Z').replace(' ', 'T')
        gps_panel = [r for r in res.json()['result'] if r['Name'] == title][0]
        self.assertEqual(gps_panel['CurrentCreated'], current_time)

        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gps_public.panel.name,))).json()
        self.assertEqual(r['result']['Created'], current_time)

    def test_get_search_gene(self):
        url = reverse_lazy('webservices:search_genes', args=(self.gpes.gene_core.gene_symbol,))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_search_by_gene(self):
        url = reverse_lazy('webservices:search_genes', args=(self.gpes.gene_core.gene_symbol,))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?ModeOfInheritance={}".format(url, self.gpes.moi))
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?ModeOfPathogenicity={}".format(url, self.gpes.mode_of_pathogenicity))
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?LevelOfConfidence={}".format(url, self.gpes.saved_gel_status))
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?Penetrance={}".format(url, self.gpes.penetrance))
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?Evidences={}".format(url, self.gpes.evidence.first().name))
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?panel_name={}".format(url, self.gps.panel.name))
        self.assertEqual(r.status_code, 200)

        multi_genes_arg = "{},{}".format(self.genes[0].gene_core.gene_symbol, self.genes[1].gene_core.gene_symbol)
        multi_genes_url = reverse_lazy('webservices:search_genes', args=(multi_genes_arg,))
        r = self.client.get(multi_genes_url)
        self.assertEqual(r.status_code, 200)

    def test_strs_in_panel(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.str.panel.panel.pk,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['result']['STRs'][0]['Name'], self.str.name)
        self.assertEqual(r.json()['result']['STRs'][0]['GRCh37Coordinates'],
                         [self.str.position_37.lower, self.str.position_37.upper])
        self.assertEqual(r.json()['result']['STRs'][0]['GRCh38Coordinates'],
                         [self.str.position_38.lower, self.str.position_38.upper])
        self.assertEqual(r.json()['result']['STRs'][0]['PathogenicRepeats'], self.str.pathogenic_repeats)

    def test_super_panel(self):
        super_panel = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        super_panel.child_panels.set([self.gps_public, ])

        r_direct = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gps_public.panel.pk,)))
        result_genes = list(sorted(r_direct.json()['result']['Genes'], key=lambda x: x.get('GeneSymbol')))

        r = self.client.get(reverse_lazy('webservices:get_panel', args=(super_panel.panel.pk,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(result_genes, list(sorted(r.json()['result']['Genes'], key=lambda x: x.get('GeneSymbol'))))

    def test_no_loss_of_function(self):
        url = reverse_lazy('webservices:search_genes', args=(self.gpes.gene_core.gene_symbol,))
        r = self.client.get("{}?ModeOfPathogenicity={}".format(url, 'no_loss_of_function'))
        self.assertEqual(len(r.json()['results']), 0)

        self.gpes.mode_of_pathogenicity = convert_mop('no_loss_of_function', back=True)
        self.gpes.save()

        r = self.client.get("{}?ModeOfPathogenicity={}".format(url, 'no_loss_of_function'))
        self.assertEqual(len(r.json()['results']), 1)
        self.assertEqual(r.json()['results'][0]['GeneSymbol'], self.gpes.gene.get('gene_symbol'))

    def test_region_in_panel(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.region.panel.panel.pk,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['result']['Regions'][0]['Name'], self.region.name)
        self.assertEqual(r.json()['result']['Regions'][0]['GRCh37Coordinates'],
                         [self.region.position_37.lower, self.region.position_37.upper])
        self.assertEqual(r.json()['result']['Regions'][0]['GRCh38Coordinates'],
                         [self.region.position_38.lower, self.region.position_38.upper])
        self.assertEqual(r.json()['result']['Regions'][0]['TriplosensitivityScore'], self.region.triplosensitivity_score)
        self.assertEqual(r.json()['result']['Regions'][0]['TypeOfVariants'], self.region.type_of_variants)

    def test_region_in_panel_empty_pos37(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.region2.panel.panel.pk,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['result']['Regions'][0]['Name'], self.region2.name)
        self.assertEqual(r.json()['result']['Regions'][0]['GRCh37Coordinates'], None)
        self.assertEqual(r.json()['result']['Regions'][0]['GRCh38Coordinates'],
                         [self.region2.position_38.lower, self.region2.position_38.upper])
        self.assertEqual(r.json()['result']['Regions'][0]['TriplosensitivityScore'], self.region2.triplosensitivity_score)
        self.assertEqual(r.json()['result']['Regions'][0]['TypeOfVariants'], self.region2.type_of_variants)

    def test_region_filters(self):
        url = reverse_lazy('webservices:get_panel', args=(self.region.panel.panel.pk,))
        r = self.client.get("{}?HaploinsufficiencyScore={}".format(url, self.region.haploinsufficiency_score)).json()
        self.assertEqual(r['result']['Regions'][0]['HaploinsufficiencyScore'], self.region.haploinsufficiency_score)

        r = self.client.get("{}?TriplosensitivityScore={}".format(url, self.region.triplosensitivity_score)).json()
        self.assertEqual(r['result']['Regions'][0]['TriplosensitivityScore'], self.region.triplosensitivity_score)

    def test_list_entities(self):
        url = reverse_lazy('webservices:list_entities')
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        res = r.json()
        self.assertEqual(len(res['results']), 8)
        self.assertEqual(len([r for r in res['results'] if r['EntityType'] == 'str']), 1)
        self.assertEqual(len([r for r in res['results'] if r['EntityType'] == 'region']), 2)
