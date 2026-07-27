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

## Approach, tools, assumptions, and trade-offs

### Approach

Vesper uses a deliberately small, human-in-the-loop pipeline:

1. A reviewer enters expected application values and uploads one label image.
2. The image is corrected for EXIF orientation, enlarged when needed, converted
   to grayscale, contrast-enhanced, and sharpened.
3. Local OCR reads the image at four rotations so sideways and upside-down
   artwork can still be evaluated.
4. Deterministic rules extract regulated values and compare them with the
   application. Text normalization and conservative fuzzy matching are used for
   brand and class/type text.
5. The interface reports `Match`, `Possible Match`, `Mismatch`, or
   `Unable to Determine`, with the evidence for each field. A human reviewer
   makes the final decision.

### Tools used

- Python 3.11
- Streamlit for the single-page user interface
- RapidOCR with ONNX Runtime for local, network-independent OCR
- Pillow and NumPy for in-memory image preprocessing
- Python `unittest` and pytest-compatible tests for automated verification

### Assumptions

- The prototype is limited to distilled spirits and the five requested
  comparison areas: brand name, class/type, alcohol content, net contents, and
  the Government Health Warning Statement. Proof is checked when it appears.
- The expected values entered by the reviewer accurately represent the
  application.
- One uploaded image contains enough readable label artwork for the requested
  checks. Bottler/producer name and address and country of origin are outside
  this prototype's comparison scope.
- Files are processed in memory. The application has no database, object store,
  analytics payload, or COLAs Online integration and does not intentionally
  retain uploaded artwork or extracted text.
- Results near a textual threshold or affected by OCR uncertainty require human
  review.

### Trade-offs

- Local OCR avoids transmitting sensitive label artwork to an external OCR
  service and works in restricted-network environments, at the cost of a larger
  deployment image, higher memory use, and slower cold starts.
- Trying four orientations improves handling of rotated artwork but can take
  longer than a single OCR pass.
- Deterministic comparisons are explainable and repeatable, but cannot determine
  whether wording is legally misleading or evaluate every conditional labeling
  requirement.
- The prototype handles one label at a time. Batch processing was intentionally
  deferred because it is valuable but not a mandatory deliverable.

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

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

## Test

```powershell
python -m unittest discover -s tests -v
```

## Public deployment

Live prototype: [ttb-alcohol-label-verifier.streamlit.app](https://ttb-alcohol-label-verifier.streamlit.app/)

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
  bottler/producer address, origin statement, formula requirement, age statement,
  or COLA requirement.
- Final determinations remain with qualified reviewers and TTB.
