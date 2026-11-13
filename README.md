# First 30 Days: what should WHOOP do when a member stops training?

**Live site: https://sudamshurao.github.io/whoop-first-30-days/**

An end-to-end product analysis on public data, built as a work sample for a Product Analyst role at WHOOP. It asks where a proactive message (such as a Coach check-in) could matter most, and how WHOOP should test it. The answer it reaches: **test one specific check-in on day 14 of a lapse, randomized per member, judged week by week**, with a sized test plan.

| Page | Question | Data |
|---|---|---|
| [Data audit](https://sudamshurao.github.io/whoop-first-30-days/audit.html) | What can each dataset support, and what can't it? | all |
| [Lapses & returns](https://sudamshurao.github.io/whoop-first-30-days/funnel.html) | How often do members stop training, and who comes back? | Endomondo (FitRec) |
| [Experiment readout](https://sudamshurao.github.io/whoop-first-30-days/readout.html) | Does a nudge change behaviour, and does the effect last? | HeartSteps V1 |
| [30-day memo](https://sudamshurao.github.io/whoop-first-30-days/memo.html) | What should WHOOP test, and how big must the test be? | all, plus Google Play reviews |

Every number on the analysis pages is computed from the dbt marts when the site is built; none is typed in by hand.

## Stack

```
public files ──► dbt staging ──► dbt intermediate ──► dbt marts ──► Python analysis ──► Quarto site
(Endomondo, HeartSteps,   clean, typed,    gaps, lapses,       facts and      survival, WCLS,     GitHub Pages
 Google Play reviews)     tested           decision points     dimensions     power
```

DuckDB · dbt-core 1.x with dbt-duckdb · Python 3.12 (pandas, statsmodels, scipy) · Quarto · uv · GitHub Actions

## Reproduce it

Requires [uv](https://docs.astral.sh/uv/) and [Quarto](https://quarto.org/). The raw data (about 1 GB) is downloaded, not stored in the repo.

```bash
uv sync
uv run python scripts/download_heartsteps.py
uv run python scripts/download_endomondo.py && uv run python scripts/flatten_endomondo.py
uv run python scripts/download_reviews.py      # newest reviews, so later runs will differ
make build                                     # dbt build: models, seeds and tests
make site                                      # renders the site into site/_site
```

## Decisions log

Choices a reviewer might question, and why they were made.

**Data and scope**
- **Endomondo is used for lapses, not activation or retention.** The dataset holds only members with long histories, so any "new member" funnel would be survivorship bias. It does support lapses among established members. See the data audit.
- **The Endomondo window ends on 2016-01-01.** A single stray January 2016 workout had set the data end, which made almost every member look lapsed (1,363 censored lapses). Fixing the end date dropped 54 workouts and cut censored lapses to 648. 213 workouts with impossible dates are also excluded.
- **A lapse is 14+ days without a workout.** A personal threshold (3x the member's usual gap) was tested and rejected: most members train almost daily, so it flagged long weekends as lapses.
- **"Back within 14 days" is counted in whole days**, in both the Kaplan-Meier curves and the mart flag. An earlier mart flag used exact time and disagreed with the site (53.4% vs 55.2%); they now agree.

**Pipeline**
- **dbt-core 1.x**, because DuckDB support in dbt 2 is still beta.
- **Staging models are tables, not views.** The sources read files by relative path, which breaks when a view is queried from outside the dbt folder.
- **Everything runs in UTC** (profile setting plus explicit UTC literals). A time-zone-dependent comparison had produced 10,323 lapses in one place and 10,321 in another.
- **Analysis pages read only marts.** The data audit is the exception, deliberately: it audits the raw files.

**Analysis**
- **No look-ahead.** A "slowdown before a lapse" baseline first used each member's whole history, future included. It was replaced with the 12 weeks before the lapse, which shrank the effect by more than half.
- **The HeartSteps readout was pre-registered in git.** The analysis plan (commit `e39c0a7`) was committed before any outcome was compared; results came afterwards (`b3e15ea`). With a constant randomization probability, the weighted and centred least squares estimator for micro-randomized trials reduces to OLS on the centred treatment, with standard errors clustered by participant (t distribution, 36 degrees of freedom). The primary analysis is complete-case; zero-filling missing outcomes is the sensitivity check. The sample matches the published one (6,331 decision points).
- **The test plan enrols each member once.** A member's lapses resemble each other, so counting every lapse would understate uncertainty. The sample-size formula was checked by simulation on the real lapse outcomes.

**Reviews**
- **No reviewer names are stored, and raw review text is not committed.** Only IDs and labels are in the repo.
- **The keyword rules were frozen before testing** (git tag `rules-v2-frozen`) and checked blind against 60 hand-labelled reviews.
- **The validation mostly failed, and the site says so.** Two labelling passes by one person agreed poorly until generic praise was handled as its own category; on the blind test, only the data-accuracy rule held up. The memo therefore claims no theme shares and cites word-level evidence instead.

**Site**
- **Quarto, not Evidence.** The Evidence open-source template had become an account-based product during the build.
- **`freeze: auto`.** Results are saved in `site/_freeze`, so the GitHub Action republishes without the data. Run `make site` before committing page changes.

## Data and credits

- **HeartSteps V1**: Klasnja et al. (2019), micro-randomized trial of activity suggestions. CC BY 4.0.
- **FitRec / Endomondo**: Ni, Muhlstein and McAuley (2019), "Modeling heart rate and activity data for personalized fitness recommendation". Used for research; see the dataset page for terms.
- **Google Play reviews** of the WHOOP app (`com.whoop.android`), public, English, US store.

No WHOOP internal data is used. This is an independent project, not affiliated with WHOOP.
