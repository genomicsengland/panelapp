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
from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO
from panels.tests.factories import GeneFactory
from panels.models import Gene


class ActivateGenesTest(TestCase):
    def test_activate_genes_output(self):
        out = StringIO()

        GeneFactory.create_batch(3, active=True)
        GeneFactory.create_batch(4, active=False, ensembl_genes='{}')
        GeneFactory.create_batch(5, active=False, ensembl_genes='{"hello": "world"}')

        call_command('activate_genes', stdout=out)
        self.assertIn('5 genes should be active', out.getvalue())
        self.assertEqual(8, Gene.objects.filter(active=True).count())
