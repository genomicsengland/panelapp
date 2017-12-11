Refactor Gene Panel statuses
============================

# Current implementation

Currently we have a `boolean` flag `approved` for setting if panel is approved or no.

Additionally, when GenePanel is deleted from the fronetned we don't actually delete it, we just set `removed` field to `True`

We are using these fields as follwing:

- Non approved panels are not visible to the users via list of panels, only to the GeL curation team, but they are visible via webservices (individual panels, not the list of panels)
- Removed are not visible on the frontend or list of panels, only `get_panel` webservice endpoint returns it
- The above can be displayed in `list_panels` API endpoint if `Retired=True` is provided in the URL.

# Proposed changes

## Enum

We can refactor the current fields just to have a single Enum field which will store the `status` of the panel, for example: `removed`, `hidden`, `internal`, `public`.

## Bitfield

Alternatively we can use a [django-bitfield](https://pypi.org/project/django-bitfield/) packages, so we can combine statuses together, for example, a panel can be public / internal and published or not.

# Changes required for the either solution

0. [/] Tests - change tests so they fail before we start the work
1. [x] Change `GenePanel` model
2. [x] Change admin panel so GeL curators and other admin users can change the status
3. [x] Change the frontend, so some statuses (i.e. approved / not approved) can be updated from the list of panels
4. [x] Change list of panels so we can filter correctly
5. [x] Change list of panels in webservices
6. [x] Change get panel in webservices
7. [x] Change get panel in frontend to use correct statuses
8. [x] Duplicate. Make sure it's possible to change status from admin panel
9. [x] Add status to JSON responses (both list and get)
10. [ ] Add status to the page if it's not published, or if user is GeL curator
11. [x] Add these filters to the `GenePanelManager` and `GenePanelSnapshotManager`
12. [x] Add the status to TSV downalod file (panel)
13. [x] Make sure we don't add activity for non-active panels (?)
14. [x] Migrate the data to use the new field
15. [x] Change all the queries to use new status field
16. [x] Change admin views
