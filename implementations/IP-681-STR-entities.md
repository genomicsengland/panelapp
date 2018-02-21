# STRs

## Model

- Name (Required)
- Chr:Position (Required)
- Repeated sequence (Required)
- Normal range
- Pre-pathogenic range
- Pathogenic range (Required)
- Gene name (Required)
- Gene data (JSON) (Required)

Ranges are: Start-End

Evaluations, comments stay the same.

These STRs also should keep the same items as the genepanelentrysnapshot + allele origin

## Checklist

- [*] Create new models
- [*] Refactor representation so we can reuse methods between entities
- [*] Add new fields to dict_tr and get_form_initial
- [*] Create migrations
- [*] Refactor increment version
- [*] Change models (stats), so it can be pre-fetched
- [-] Change models so STR data and users are prefetched as well
- [*] Add track records
- [*] Change activities so it supports STRs
- [*] List of STRs in a panel
- [*] Change templates (panels)
- [*] Forms
- [*] Making sure it's all added to the activities
- [*] Add new templates and pages for STRs
- [*] Change urls /panels/<panel id>/<gene symbol> -> /panels/<panel id>/gene/<gene symbol> so we can add /panels/<panel id>/str/<name>
- [*] Support previous URLs
- [ ] Webservices changes
- [ ] Export STR data and reviews (?)
- [ ] Import STR reviews
- [*] Make sure indexes are in place for complex queries
- [*] Add database aggregates for STRs
- [*] Tests
- [ ] Copy STR reviews
- [ ] Compare panels changes

## Changes

There will be a few changes required for the implementation, for example gene activities and track records will change slightly.

Activity pages will be different too as we will have STRs as well, and plan how this would look in the future.
