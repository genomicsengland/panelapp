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
from django.test import TestCase
from panels.tests.factories import GenePanelEntrySnapshotFactory


class RedirectsTests(TestCase):
    def test_homepage(self):
        res = self.client.get('/crowdsourcing')
        self.assertEqual(res.status_code, 301)

    def test_panelapp_homepage(self):
        res = self.client.get('/crowdsourcing/PanelApp/')
        self.assertEqual(res.status_code, 301)

    def test_genes(self):
        res = self.client.get('/crowdsourcing/PanelApp/Genes')
        self.assertEqual(res.status_code, 301)

    def test_gene(self):
        res = self.client.get('/crowdsourcing/PanelApp/Genes/ABC')
        self.assertEqual(res.status_code, 301)

    def test_panels_list(self):
        res = self.client.get('/crowdsourcing/PanelApp/PanelBrowser')
        self.assertEqual(res.status_code, 301)

    def test_view_panel(self):
        res = self.client.get('/crowdsourcing/PanelApp/EditPanel/558aa423bb5a16630e15b63c')
        self.assertEqual(res.status_code, 301)

    def test_view_panel_gene(self):
        res = self.client.get('/crowdsourcing/PanelApp/GeneReview/558aa423bb5a16630e15b63c/NTRK1')
        self.assertEqual(res.status_code, 301)

    def test_webservices(self):
        res = self.client.get('/crowdsourcing/WebServices/list_panels')
        self.assertEqual(res.status_code, 301)

    def test_specific_versions(self):
        gpes = GenePanelEntrySnapshotFactory()
        res = self.client.get('/crowdsourcing/WebServices/get_panel/{}?version=0.0'.format(gpes.panel.id))
        self.assertIn('version=0.0', res.url)
        self.assertEqual(res.status_code, 301)
