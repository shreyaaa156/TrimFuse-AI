# TrimFuse AI — Implementation Report

## Objective
Build an AI-assisted workflow for derivative-chip trim prediction and fuse-map validation using the supplied synthetic assessment datasets.

## Implemented modules
- MCU bandgap, HSI and LDO trim-code prediction using HistGradientBoosting, RandomForest and ExtraTrees candidate models.
- Wafer-grouped holdout evaluation to reduce leakage between correlated dies.
- Derivative-aware fuse-word checks for flash-size encoding, peripheral mask, debug lock, read protection and reserved bits.
- Dataset insight views for PMIC coupled rails, sensor temperature calibration, SoC Fmax/binning and memory repair.
- Streamlit UI with downloadable fuse-audit output.

## Data and validation
The supplied README states that all datasets are synthetic. MCU-A model evaluation uses a held-out wafer split. Metrics are generated in the app and depend on the deterministic split and installed scikit-learn version. The supplied baseline result file reports: bandgap 97.9% within ±1 code, HSI 80.4%, LDO 99.9%; MCU-C drift transfer MAE improves from 1.73 mV to 0.86 mV after 50-die fine-tuning; fuse audit catches 406/406 injected errors with zero false alarms.

## Safety controls and limitations
Predictions are recommendations only. A tester verification measurement, hard code limits, deterministic fuse schema checks and conventional-search fallback are required. Security/key fuses must remain on audited deterministic flows. No real OTP fuse programming is performed. Synthetic data cannot establish production performance; retraining and validation on real STDF/PCM and tester data are required.

## Run
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
