import os
import ijson
try:
    import ujson as json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from accounts.models import Reviewer

from panelapp.models import Image
from panelapp.models import HomeText

from panels.models import UploadedGeneList
from panels.models import UploadedPanelList
from panels.models import UploadedReviewsList
from panels.models import Gene
from panels.models import Level4Title
from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.models import Activity

from panels.models import Evidence
from panels.models import Evaluation
from panels.models import Tag
from panels.models import TrackRecord
from panels.models import GenePanelEntrySnapshot
from panels.models import Comment
from panels.models.import_tools import update_gene_collection


class Command(BaseCommand):
    def __init__(self):
        super().__init__()
        self.files_path = None
        self.genes = {}
        self.gene_panels = {}
        self.gene_panel_snapshots = {}
        self.users = {}
        self.tz = timezone.get_current_timezone()

    def add_arguments(self, parser):
        parser.add_argument('dump_path', type=str, help="Full path to the dump location")
        parser.add_argument('--backups_only', action='store_true', dest='backups_only', default=False, help="Only import panel backups")

    def handle(self, dump_path, backups_only, *args, **options):
        if not os.path.isdir(dump_path):
            self.stderr.write("Can't find v1 dump location")
            os.sys.exit(1)

        self.files_path = dump_path

        if not os.path.isfile(os.path.join(self.files_path, 'new_genes.json')):
            self.stderr.write("Can't find new genes JSON file")
            os.sys.exit(1)

        with transaction.atomic():
            if backups_only is True:
                self.load_users_from_database()
                self.load_genes_from_database()
                self.import_backup_panels()
            else:
                self.import_users()
                self.import_admin_files()
                self.import_genes()
                self.import_gene_panels()
                self.import_activities()
                self.import_gene_panel_entries()
                self.migrate_genes()

    def _iterate_file(self, filename, json_path):
        with open(os.path.join(self.files_path, filename), 'r') as f:
            items = ijson.items(f, json_path)
            for item in items:
                yield item

    def migrate_genes(self):
        with open(os.path.join(self.files_path, 'new_genes.json'), 'r') as genes_json:
            update_gene_collection(json.load(genes_json))

    def load_users_from_database(self):
        for user in User.objects.all():
            self.users[user.username] = user

    def load_genes_from_database(self):
        for gene in Gene.objects.all():
            self.genes[gene.gene_symbol] = gene

    def import_backup_panels(self):
        total = 0
        for gp in self._iterate_file('gene_panel_backups.json', 'gene_backups.item'):
            total += 1
            if total % 100 == 0:
                print('total backup panels created: {}'.format(total))

            _gp = self.gene_panels.get(gp['pk'])
            if not _gp:
                try:
                    _gp = GenePanel.objects.get(old_pk=gp['pk'])
                except GenePanel.DoesNotExist:
                    _gp = self.create_gene_panel(gp)

            gps = self.create_gene_panel_snapshot(gp, _gp)

            for gpe in gp['panellist']:
                gpe['ready'] = False
                self.create_gene_panel_entry_snapshot(gpe, gps)

        self.stdout.write('Created {} backup panels'.format(total))

    def create_gene_panel_entry_snapshot(self, gpe, panel):
        if gpe['gene']['gene_symbol'][-1] == '*':
            gpe['gene']['gene_symbol'] = gpe['gene']['gene_symbol'][:-1]

        gene = self.genes.get(gpe['gene']['gene_symbol'])

        if not gene:
            try:
                gene = Gene.objects.get(gene_symbol=gpe['gene']['gene_symbol'])
                self.genes[gpe['gene']['gene_symbol']] = gene
            except Gene.DoesNotExist:
                gene = Gene.objects.create(
                    gene_symbol=gpe['gene']['gene_symbol'],
                    gene_name=gpe['gene']['gene_name'],
                    omim_gene=[gpe['gene']['omim_gene'],],
                    ensembl_genes="{}",
                    active=False
                )
                self.stdout.write("Gene:{} not in database, creating".format(gpe['gene']['gene_symbol']))

        try:
            gel_status = gpe['track'][-1]['gel_status']
            if gpe['flagged']:
                gel_status = 0
            elif gel_status < 2:
                gel_status = 1
            elif gel_status == 2:
                gel_status = 2
            else:
                gel_status = 3
        except IndexError:
            gel_status = 0

        gpes = GenePanelEntrySnapshot.objects.create(
            panel=panel,
            gene=gpe['gene'],
            gene_core=gene,
            moi=gpe['moi'],
            penetrance=gpe['penetrance'],
            publications=[p for p in gpe['publications'] if p],
            phenotypes=[p for p in gpe['phenotypes'] if p],
            flagged=gpe['flagged'],
            ready=gpe['ready'],
            mode_of_pathogenicity=gpe['mode_of_pathogenicity'],
            saved_gel_status=gel_status
        )

        for evidence in gpe['evidence']:
            date = timezone.make_aware(convert_date(evidence['date']), self.tz)
            ev = Evidence.objects.create(
                name=evidence['name'],
                rating=evidence['rating'],
                comment=evidence['comment'],
                legacy_type=evidence['type'],
                created=date,
                modified=date
            )

            gpes.evidence.add(ev)

        for evaluation in gpe['evaluation']:
            if evaluation['rating']:
                r = evaluation['rating'].lower()
                if r == 'green list (high evidence)' or r == 'green':
                    r = "GREEN"
                elif r == 'red' or r == 'red list (low evidence)':
                    r = "RED"
                elif r == 'amber' or r == "i don't know":
                    r = "AMBER"
            else:
                r = ''

            user = self.get_create_user(evaluation['user'])
            if evaluation['publications']:
                publications = [p for p in evaluation['publications'] if p]
            else:
                publications = None
            if evaluation['phenotypes']:
                phenotypes = [p for p in evaluation['phenotypes'] if p]
            else:
                phenotypes = None

            if evaluation['date']:
                date = timezone.make_aware(convert_date(evaluation['date']), self.tz)
            else:
                if evaluation['comments']:
                    date = timezone.make_aware(convert_date(evaluation['comments'][0]['date']), self.tz)
                else:
                    date = timezone.now()

            ev = Evaluation.objects.create(
                user=user,
                rating=r,
                mode_of_pathogenicity=evaluation['mode_of_pathogenicity'],
                publications=publications,
                phenotypes=phenotypes,
                moi=evaluation['moi'],
                current_diagnostic=evaluation['current_diagnostic'],
                version=evaluation['version'],
                created=date,
                modified=date
            )
            gpes.evaluation.add(ev)

            for comment in evaluation['comments']:
                date = timezone.make_aware(convert_date(comment['date']), self.tz)
                c = Comment.objects.create(
                    user=user,
                    comment=comment['comment'],
                    created=date,
                    modified=date
                )
                ev.comments.add(c)

        for track in gpe['track']:
            # we've changed the issue types
            # here we iterate over the old values and try to match them to
            # the new values

            issue_type = track['issue_type']
            issue_types = [it.strip().lower() for it in issue_type.split(',') if it]
            new_it = set()
            for it in issue_types:
                new_match = None
                for t in TrackRecord.ISSUE_TYPES:
                    if t[1].lower() == it:
                        new_match = t[0]
                        break
                    elif "set mode of inheritance" == it:
                        new_match = "SetModelofInheritance"
                        break

                if new_match:
                    new_it.add(new_match)
                else:
                    new_it.add(it)

            track_user = self.users.get(track['user'])
            if not track_user:
                track_user = self.users[track['user']] = User.objects.create(
                    username=track['user'],
                    first_name=track['user']
                )
                
                Reviewer.objects.create(
                    user=self.users[track['user']],
                    user_type="REVIEWER",
                    role="Other",
                    workplace="Other",
                    group="Other"
                )

            date = timezone.make_aware(convert_date(track['date']), self.tz)
            t = TrackRecord.objects.create(
                created=date,
                modified=date,
                user=track_user,
                gel_status=track['gel_status'],
                curator_status=track['curator_status'],
                issue_type=",".join(new_it),
                issue_description=track['issue_description']
            )
            gpes.track.add(t)

        for tag in gpe['tags']:
            if tag:
                t = Tag.objects.get_or_create(
                    name=tag
                )
                gpes.tags.add(t[0])

        if gpe.get('curator_comments'):
            for comment in gpe['curator_comments']:
                date = timezone.make_aware(convert_date(comment['date']), self.tz)
                c = Comment.objects.create(
                    user=self.users[comment['user']],
                    comment=comment['comment'],
                    created=date,
                    modified=date
                )
                gpes.comments.add(c)

    def import_gene_panel_entries(self):
        total = 0
        for gpe in self._iterate_file('gene_panel_entries.json', 'gene_panel_entries.item'):
            total += 1

            panel = self.gene_panel_snapshots[gpe['panel_pk']]
            self.create_gene_panel_entry_snapshot(gpe, panel)

            if total % 5000 == 0:
                self.stdout.write('Created {} gene panel entries'.format(total))

        self.stdout.write('Created {} gene panel entries in total'.format(total))

    def import_activities(self):
        total = 0
        missed = 0

        for a in self._iterate_file('activities.json', 'activities.item'):
            panel = self.gene_panels.get(a['panel_id'])
            user = self.users.get(a['user'])
            if user and (not a['panel_id'] or a['panel_id'] and panel):
                total += 1
                date = timezone.make_aware(convert_date(a['date']), self.tz)
                Activity.objects.create(
                    panel=panel,
                    gene_symbol=a['gene_symbol'],
                    user=user,
                    text=a['text'],
                    created=date,
                    modified=date
                )
            else:
                missed += 1
        self.stdout.write('Created {} activities, missed {}'.format(total, missed))

    def create_gene_panel(self, gp):
        _gp = GenePanel.objects.create(
            old_pk=gp['pk'],
            name=gp['panel_name'],
            approved=gp['approved']
        )
        return _gp

    def create_gene_panel_snapshot(self, gp, _gp):
        l4t = gp['level4title']
        _l4t = Level4Title.objects.create(
            name=l4t['name'],
            description=l4t['description'].encode('utf8', 'replace'),
            level3title=l4t['level3title'],
            level2title=l4t['level2title'],
            omim=[o for o in l4t['omim'] if o],
            orphanet=[o for o in l4t['orphanet'] if o],
            hpo=[h for h in l4t['hpo'] if h]
        )

        _gps = GenePanelSnapshot.objects.create(
            panel=_gp,
            level4title=_l4t,
            major_version=gp['major_version'],
            minor_version=gp['minor_version'],
            version_comment=gp['version_comment'],
            old_panels=gp['old_panels']
        )
        return _gps

    def import_gene_panels(self):
        total = 0
        for gp in self._iterate_file('gene_panels.json', 'gene_panels.item'):
            total += 1

            _gp = self.create_gene_panel(gp)
            self.gene_panels[gp['pk']] = _gp
            _gps = self.create_gene_panel_snapshot(gp, _gp)

            self.gene_panel_snapshots[gp['pk']] = _gps

        self.stdout.write('Created {} gene panels'.format(total))

    def import_genes(self):
        total = 0
        for gene in self._iterate_file('genes.json', 'genes.item'):
            if gene['gene_symbol'][-1] == "*":
                gene['gene_symbol'] = gene['gene_symbol'][:-1]

            total += 1

            g = Gene.objects.create(
                gene_symbol=gene['gene_symbol'],
                gene_name=gene['gene_name'],
                omim_gene=[gene['omim_gene'],],
                ensembl_genes="{}"
            )
            self.genes[g.gene_symbol] = g

        self.stdout.write('Created {} genes'.format(total))

    def import_admin_files(self):
        total = 0
        for image in self._iterate_file('admin.json', 'images.item'):
            total += 1
            img = Image()
            img.image.name = image['image']
            img.alt = ""
            img.save()
        self.stdout.write('Created {} images'.format(total))

        total = 0
        for ht in self._iterate_file('admin.json', 'hometext.item'):
            total += 1

            s = int(ht['section'])
            print('-'*80)
            print(s)

            if s == 1:
                title = "Home"
                href = "Introduction"
            elif s == 2:
                title = "Gene Panel Guidelines"
                href = "Principles"
            elif s == 3:
                title = "The Role of Expert Reviewers"
                href = "Reviewers"
            elif s == 4:
                title = "News"
                href = "Guidelines"
            elif s == 5:
                title = "PanelApp Instructions"
                href = "Instructions"
            elif s == 6:
                title = "How to..."
                href = "HowTo"
            elif s == 7:
                title = "FAQs"
                href = "FAQs"
            elif s == 8:
                title = "Contact, Sources and Glossary"
                href = "Information"
            else:
                title = ht['text'][:10]
                href = ht['text'][:10]
            
            text = ht['text'].replace('/static/uploads/', '/media/')
            text = text.replace(
                'https://panelapp.extge.co.uk/crowdsourcing/PanelApp/',
                'https://panelapp.extge.co.uk'
            )

            if HomeText.objects.filter(href=href).count() == 0:
                ht = HomeText.objects.create(
                    section=s,
                    text=text,
                    title=title,
                    href=href
                )
        self.stdout.write('Created {} home texts'.format(total))

        total = 0
        for gl in self._iterate_file('admin.json', 'genelist.item'):
            total += 1
            _gl = UploadedGeneList()
            _gl.gene_list.name = gl['gene_list']
            _gl.imported = True
            _gl.save()
        self.stdout.write('Created {} gene lists'.format(total))

        total = 0
        for pl in self._iterate_file('admin.json', 'panellist.item'):
            total += 1
            _pl = UploadedPanelList()
            _pl.panel_list.name = pl['panel_list']
            _pl.imported = True
            _pl.save()
        self.stdout.write('Created {} panel lists'.format(total))

        total = 0
        for r in self._iterate_file('admin.json', 'reviews.item'):
            total += 1
            _r = UploadedReviewsList()
            _r.reviews.name = r['reviews']
            _r.imported = True
            _r.save()
        self.stdout.write('Created {} review lists'.format(total))

    def get_create_user(self, username):
        "Get user from local cache or create if it doesn't exist"

        try:
            user = self.users[username]
        except KeyError:
            user = User.objects.create(
                username=username,
                is_superuser=False,
                is_staff=False,
                is_active=False,
                email='uknown-user-{}@example.com'.format(username),
                first_name='',
                last_name=''
            )

            Reviewer.objects.create(
                user=user,
                user_type=Reviewer.TYPES.EXTERNAL,
                affiliation='',
                workplace=Reviewer.WORKPLACES.Other,
                role=Reviewer.ROLES.Other,
                group=Reviewer.GROUPS.Other
            )
            self.users[username] = user

        return user

    def import_users(self):
        total = 0
        for user in self._iterate_file('users.json', 'users.item'):
            total += 1
            date = timezone.make_aware(convert_date(user['date_joined']), self.tz)
            u = User.objects.create(
                first_name=user['first_name'],
                last_name=user['last_name'],
                email=user['email'],
                created=date,
                is_staff=user['is_staff'],
                username=user['username'],
                password=user['password'],
                date_joined=date,
                is_superuser=user['is_superuser']
            )
            self.users[user['username']] = u
            Reviewer.objects.create(
                user=u,
                user_type=user['reviewers']['user_type'],
                affiliation=user['reviewers']['affiliation'],
                workplace=user['reviewers']['workplace'],
                role=user['reviewers']['role'],
                group=user['reviewers']['group']
            )
        self.stdout.write('Created {} users'.format(total))


def convert_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
    except ValueError:
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
