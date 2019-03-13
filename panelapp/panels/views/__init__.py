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
from .panels import AdminView
from .panels import AdminUploadGenesView
from .panels import AdminUploadPanelsView
from .panels import AdminUploadReviewsView
from .panels import DownloadAllPanels
from .panels import ActivityListView
from .panels import CreatePanelView
from .panels import GenePanelView
from .panels import PanelsIndexView
from .panels import UpdatePanelView
from .panels import PromotePanelView
from .panels import OldCodeURLRedirect
from .genes import DownloadPanelTSVView
from .genes import DownloadPanelVersionTSVView
from .genes import ComparePanelsView
from .genes import CompareGeneView
from .genes import CopyReviewsView
from .genes import DownloadAllGenes
from .entities import EntityReviewView
from .entities import PanelEditEntityView
from .entities import PanelAddEntityView
from .entities import PanelMarkNotReadyView
from .entities import GenePanelSpanshotView
from .entities import MarkEntityReadyView
from .entities import MarkGeneNotReadyView
from .entities import EntityDetailView
from .entities import EntitiesListView
from .entities import GeneDetailRedirectView
from .entities import RedirectGenesToEntities
from .strs import DownloadAllSTRs
from .regions import DownloadAllRegions
