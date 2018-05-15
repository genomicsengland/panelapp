# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-05-14 10:37
from __future__ import unicode_literals

import django.contrib.postgres.fields
import django.contrib.postgres.fields.jsonb
import django.contrib.postgres.fields.ranges
import django.core.serializers.json
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import panels.models.entity


class Migration(migrations.Migration):

    dependencies = [
        ('panels', '0048_auto_20180514_1027'),
    ]

    operations = [
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(max_length=128)),
                ('chromosome', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'), ('15', '15'), ('16', '16'), ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20'), ('21', '21'), ('22', '22'), ('X', 'X'), ('Y', 'Y')], max_length=8)),
                ('position_37', django.contrib.postgres.fields.ranges.IntegerRangeField()),
                ('position_38', django.contrib.postgres.fields.ranges.IntegerRangeField()),
                ('type_of_variants', models.CharField(choices=[('Small', 'Small'), ('SV', 'SV'), ('CNV', 'CNV')], max_length=32)),
                ('type_of_effects', models.CharField(choices=[('transcript_ablation', 'A feature ablation whereby the deleted region includes a transcript feature'), ('splice_acceptor_variant', "A splice variant that changes the 2 base region at the 3' end of an intron"), ('splice_donor_variant', "A splice variant that changes the 2 base region at the 5' end of an intron"), ('stop_gained', 'A sequence variant whereby at least one base of a codon is changed, resulting in a premature stop codon, leading to a shortened transcript'), ('frameshift_variant', 'A sequence variant which causes a disruption of the translational reading frame, because the number of nucleotides inserted or deleted is not a multiple of three'), ('stop_lost', 'A sequence variant where at least one base of the terminator codon (stop) is changed, resulting in an elongated transcript'), ('start_lost', 'A codon variant that changes at least one base of the canonical start codon'), ('transcript_amplification', 'A feature amplification of a region containing a transcript'), ('inframe_insertion', 'An inframe non synonymous variant that inserts bases into in the coding sequence'), ('inframe_deletion', 'An inframe non synonymous variant that deletes bases from the coding sequence'), ('missense_variant', 'A sequence variant, that changes one or more bases, resulting in a different amino acid sequence but where the length is preserved'), ('protein_altering_variant', 'A sequence_variant which is predicted to change the protein encoded in the coding sequence'), ('splice_region_variant', 'A sequence variant in which a change has occurred within the region of the splice site, either within 1-3 bases of the exon or 3-8 bases of the intron'), ('incomplete_terminal_codon_variant', 'A sequence variant where at least one base of the final codon of an incompletely annotated transcript is changed'), ('start_retained_variant', 'A sequence variant where at least one base in the start codon is changed, but the start remains'), ('stop_retained_variant', 'A sequence variant where at least one base in the terminator codon is changed, but the terminator remains'), ('synonymous_variant', 'A sequence variant where there is no resulting change to the encoded amino acid'), ('coding_sequence_variant', 'A sequence variant that changes the coding sequence'), ('mature_miRNA_variant', 'A transcript variant located with the sequence of the mature miRNA'), ('5_prime_UTR_variant', "A UTR variant of the 5' UTR"), ('3_prime_UTR_variant', "A UTR variant of the 3' UTR"), ('non_coding_transcript_exon_variant', 'A sequence variant that changes non-coding exon sequence in a non-coding transcript'), ('intron_variant', 'A transcript variant occurring within an intron'), ('NMD_transcript_variant', 'A variant in a transcript that is the target of NMD'), ('non_coding_transcript_variant', 'A transcript variant of a non coding RNA gene'), ('upstream_gene_variant', "A sequence variant located 5' of a gene"), ('downstream_gene_variant', "A sequence variant located 3' of a gene"), ('TFBS_ablation', 'A feature ablation whereby the deleted region includes a transcription factor binding site'), ('TFBS_amplification', 'A feature amplification of a region containing a transcription factor binding site'), ('TF_binding_site_variant', 'A sequence variant located within a transcription factor binding site'), ('regulatory_region_ablation', 'A feature ablation whereby the deleted region includes a regulatory region'), ('regulatory_region_amplification', 'A feature amplification of a region containing a regulatory region'), ('feature_elongation', 'A sequence variant that causes the extension of a genomic feature, with regard to the reference sequence'), ('regulatory_region_variant', 'A sequence variant located within a regulatory region'), ('feature_truncation', 'A sequence variant that causes the reduction of a genomic feature, with regard to the reference sequence'), ('intergenic_variant', 'A sequence variant located in the intergenic region, between genes')], max_length=32)),
                ('gene', django.contrib.postgres.fields.jsonb.JSONField(blank=True, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True)),
                ('moi', models.CharField(choices=[('', 'Provide a mode of inheritance'), ('MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted', 'MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted'), ('MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)', 'MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)'), ('MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)', 'MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)'), ('MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown', 'MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown'), ('BIALLELIC, autosomal or pseudoautosomal', 'BIALLELIC, autosomal or pseudoautosomal'), ('BOTH monoallelic and biallelic, autosomal or pseudoautosomal', 'BOTH monoallelic and biallelic, autosomal or pseudoautosomal'), ('BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal', 'BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal'), ('X-LINKED: hemizygous mutation in males, biallelic mutations in females', 'X-LINKED: hemizygous mutation in males, biallelic mutations in females'), ('X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)', 'X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)'), ('MITOCHONDRIAL', 'MITOCHONDRIAL'), ('Unknown', 'Unknown'), ('Other - please specifiy in evaluation comments', 'Other - please specifiy in evaluation comments')], max_length=255, verbose_name='Mode of inheritance')),
                ('penetrance', models.CharField(blank=True, choices=[('unknown', 'unknown'), ('Complete', 'Complete'), ('Incomplete', 'Incomplete')], max_length=255, null=True)),
                ('publications', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), blank=True, null=True, size=None)),
                ('phenotypes', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), blank=True, null=True, size=None)),
                ('flagged', models.BooleanField(default=False)),
                ('ready', models.BooleanField(default=False)),
                ('mode_of_pathogenicity', models.CharField(blank=True, choices=[('', 'Provide exceptions to loss-of-function'), ('Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments', 'Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments'), ('Other - please provide details in the comments', 'Other - please provide details in the comments')], max_length=255, null=True)),
                ('saved_gel_status', models.IntegerField(db_index=True, null=True)),
                ('comments', models.ManyToManyField(to='panels.Comment')),
                ('evaluation', models.ManyToManyField(db_index=True, to='panels.Evaluation')),
                ('evidence', models.ManyToManyField(to='panels.Evidence')),
                ('gene_core', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='panels.Gene')),
                ('panel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='panels.GenePanelSnapshot')),
                ('tags', models.ManyToManyField(to='panels.Tag')),
                ('track', models.ManyToManyField(to='panels.TrackRecord')),
            ],
            options={
                'get_latest_by': 'created',
                'ordering': ['-saved_gel_status'],
            },
            bases=(panels.models.entity.AbstractEntity, models.Model),
        ),
        migrations.AddIndex(
            model_name='region',
            index=models.Index(fields=['panel_id'], name='panels_regi_panel_i_35b205_idx'),
        ),
        migrations.AddIndex(
            model_name='region',
            index=models.Index(fields=['gene_core_id'], name='panels_regi_gene_co_0c95f6_idx'),
        ),
        migrations.AddIndex(
            model_name='region',
            index=models.Index(fields=['name'], name='panels_regi_name_723e27_idx'),
        ),
    ]
