# Vesper Label Verifier

Vesper is a human-in-the-loop Streamlit prototype that compares expected
distilled-spirits application data with text extracted from a label image using
local OCR. It reports `Match`, `Possible Match`, `Mismatch`, or
`Unable to Determine`; it does not make a legal approval decision.

## What it checks

- Brand name and class/type text, using normalized and near-match comparison.
- A mandatory percent alcohol-by-volume statement. `ABV` alone is not accepted.
- Optional proof, when shown, equals twice the stated alcohol percentage.
- Metric net contents and the authorized standards of fill listed by TTB.
- The exact federal government health-warning wording.

OCR cannot reliably certify physical type size, bold styling, contrast,
same-field-of-vision placement, or whether wording is misleading. Vesper calls
these limitations out for human review.

## Run locally

Python 3.11 is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts\generate_samples.py
streamlit run app.py
```

The first OCR request can take longer while the local OCR engine initializes.
No uploaded label or OCR result is sent to a cloud service.

## Test

```powershell
python -m unittest discover -s tests -v
```

## Public deployment

The repository is ready for Streamlit Community Cloud: select `app.py` as the
entry point and Python 3.11. `requirements.txt` contains the runtime
dependencies. A `Procfile` is also included for platforms that launch web
processes and supply a `PORT` environment variable.

Because the OCR models increase memory and cold-start time, choose a host with
at least 1 GB RAM; 2 GB is preferable. Uploaded files are processed in memory.

## Rules authority and assumptions

Rules were reviewed July 26, 2026 against current official TTB guidance:

- [Distilled Spirits Labeling](https://www.ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/labeling)
- [Mandatory Label Information](https://www.ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/ds-labeling-home/ds-brand-label)
- [Brand Name](https://www.ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/ds-labeling-home/ds-brand-name)
- [Alcohol Content](https://www.ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/ds-labeling-home/ds-alcohol-content)
- [Net Contents](https://www.ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/ds-labeling-home/ds-net-contents)
- [Health Warning Statement](https://www.ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/ds-labeling-home/ds-health-warning)

The older Beverage Alcohol Manual is not used as the primary authority because
TTB states that it has not yet been updated to match current 27 CFR part 5.

## Limitations

- Distilled spirits only; specialty-product composition statements are not
  substantively adjudicated.
- A single uploaded image cannot prove that information on different physical
  sides of a container shares the required field of vision.
- OCR can miss text on curved, reflective, low-resolution, or decorative labels.
- The checker covers the five requested fields, not every conditional disclosure,
  origin statement, formula requirement, age statement, or COLA requirement.
- Final determinations remain with qualified reviewers and TTB.

