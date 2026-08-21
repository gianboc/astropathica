# Taxonomy seed — salvaged from mailRead (May 2026 snapshot)

> Salvaged 2026-08-21 from `gianboc/mailRead` CLAUDE.md before that repo was deleted.
> Purpose here: seed material for the **Phase 2 ledger tagger** (one-line gist +
> probable project tag per email). ⚠️ Snapshot is stale by ~3 months — refresh the
> project/people/tag lists against the vault's `projectTags.md` + `PEOPLE.md`
> before wiring into the tagger. The category schema and domain hints age slowly.

## Categorization spec

Each email should get:

| Column | Description |
|--------|-------------|
| date | Original email date |
| from_name | Sender display name |
| from_email | Sender email address |
| subject | Email subject |
| folder | Outlook folder path |
| has_attachments | Boolean |
| category | See categories below |
| subcategory | Finer grain if applicable |
| urgency | HIGH / MEDIUM / LOW / NOISE |
| action_needed | YES / NO / MAYBE |
| related_project | Project/paper codename if identifiable (see below) |
| summary | 1-line summary of what the email is about |
| notes | Any flags (e.g., "deadline mentioned", "waiting for reply") |

### Categories

- **RESEARCH_PAPER** — Related to a specific paper (submission, review, revision, collaboration)
- **PROJECT_ADMIN** — EU/Italian project admin (BATCAT, AI4CO2, PNRR, etc.)
- **PROPOSAL** — Grant proposals (REDOXWALL, PRIN, ESA, EIC, etc.)
- **TEACHING** — Courses, exams, student admin, thesis supervision
- **PHD_SUPERVISION** — PhD student matters, defense, milestones
- **DEPARTMENT** — DISAT/POLITO admin, department meetings, bureaucracy
- **CONFERENCE** — Conference submissions, invitations, organization
- **COLLABORATION** — External collaborator correspondence not tied to a specific paper
- **JOURNAL** — Journal editorial, reviewing requests, editorial board
- **IT_INFRA** — HPC, servers, software licenses, IT support
- **COMMERCIAL** — Newsletters, vendor emails, subscriptions
- **PERSONAL** — Non-work
- **NOTIFICATION** — Automated notifications (GitHub, Overleaf, calendar, etc.)
- **SPAM** — Predatory journals, irrelevant mass emails

### Project/Paper codenames to match against

**Papers (Indomitus Initiative — active research papers):**
- 01-CEFOCAT, 02-CEFOFILTER, 03-AIMFOAM, 04-BIOMET, 05-MORE
- 06-BSAND, 07-DPDL61 (published), 08A-DPD-Electrolyte (mothballed), 08B-DPD-PEGDA
- 09-LIS, 10-BIOSCAFFOLD, 11-ATLAS, 12A-BATCAT-SEI, 12B-BLENDED
- 13-BATT_HOMOG, 14-RHEOML, 15-HETERODATA, 16-RADIALPACK
- 17-PCM, 18-HOMOG, 19-KCNODE, 20-TEXTAILES_AIR (published)
- 21-LSTM (in review), 22-TEXTAILES_FIRE, 23-ECMO
- 24-PCM-SPORT, 25-JACKETS, 26-MONOLETHE, 27-F3 (horizon)

**Funded projects:**
- BATCAT (HEU), AI4CO2/CLIMIT, VIMMP (ended), SIMDOME (ended)
- PNRR-PE11 (textAIles), HOMOG/KNIT (Stanford internationalization, Fondazione CRT)
- Lavazza (industry contract)

**Proposals (pending/planning):**
- REDOXWALL (Horizon Europe), ELISA (Eni, Na-ion batteries)
- ESA FIRST!, EIC Pathfinder, PRIN 2026 (4 proposals planned)

### Key people/senders to recognize

These names in sender or subject should help with categorization:

| Name | Context |
|------|--------|
| Daniele Marchisio / marchisio | Group leader, co-author on many papers |
| Ada Ferri / ferri | Textile group PI, Alba Pluma papers |
| Eleonora Bianca / bianca | PhD, textiles + ML, papers 20-25 |
| Diego Fida / fida | PhD, papers 05-MORE, 17-PCM, 18-HOMOG. Now at Stanford. |
| Nancy / Nunzia Lauriello / lauriello | Postdoc, DPD papers 07, 08 |
| Elisa Buccafusco / buccafusco | PhD, BATCAT/battery papers 12A, 12B |
| Matteo Icardi / icardi | Nottingham, OpenFOAM, papers 05, 06 |
| Ilenia Battiato / battiato | Stanford, homogenization, papers 13, 18 |
| Agnese Marcato / marcato | RTDA, ML |
| Michel Orsi / orsi | Postdoc, paper 14-RHEOML |
| Nico / Nicodemo Di Pasquale | Bologna, papers 08, 16, 23 |
| Samir Bensaid / bensaid | PI for Diego, paper 05 |
| Silvia Bodoardo / bodoardo | Battery group, paper 09-LIS |
| Ferran Brosa Planella | Warwick, paper 17-PCM |
| Olivier Guévremont | Montreal, paper 26-MONOLETHE |
| Bruno Blais / blais | Montreal, Lethe solver |
| Martina Gilardi / gilardi | PhD student, paper 19-KCNODE |
| Andrea Querio / querio | PhD, paper 09-LIS, COMSOL |
| Maryam Ghadrdan | Planck Technologies, AI4CO2 |
| Sergio Pio Rendine / rendine | PhD, paper 10-BIOSCAFFOLD |
| Ghasem Beiginalou / beiginalou | Was PhD, paper 22 |
| Marco Vanni / vanni | Old team leader |
| Antonio Buffo / buffo | Colleague |

### Sender domain hints

| Domain pattern | Likely category |
|---------------|----------------|
| @polito.it | Internal — could be anything |
| @studenti.polito.it | Student |
| @springer, @elsevier, @wiley, @mdpi, @nature | JOURNAL or RESEARCH_PAPER |
| @editorialmanager, @manuscriptcentral, @ees.elsevier | RESEARCH_PAPER (submission system) |
| @github.com, @overleaf | NOTIFICATION |
| @europa.eu, @ec.europa.eu | PROJECT_ADMIN (EU) |
| @gassnova.no | PROJECT_ADMIN (AI4CO2/CLIMIT) |
| @stanford.edu | COLLABORATION (Battiato/HOMOG) |
| @polymtl.ca | COLLABORATION (Montreal/MONOLETHE) |
| @unibo.it | COLLABORATION (Bologna/ECMO) |
| @warwick.ac.uk | COLLABORATION (Ferran/PCM) |
| @nottingham.ac.uk | COLLABORATION (Icardi) |
| @linkedin, @researchgate, @academia.edu | NOTIFICATION or NOISE |

