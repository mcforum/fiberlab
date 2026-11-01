# Data

## `laser_diffraction_run_A04/`
Main measurement run of the diffraction station, 4 fibres × 4 samples, λ = 650 nm.
- `measurements.csv` – one row per sample (distance statistics, temperature, speed of sound, minima spacing `a`, order `m`, diameter exact and small-angle).
- `summary.csv` – per-fibre mean, SD, min, max.
- `ultrasonic_pings.csv` – all 50 raw ultrasonic distance readings per measurement.

Known issue: row 14 has a typo in `L_tape_cm` (1.0 instead of ≈ 79.9); it only affects the tape-vs-ultrasound validation column, not `d`.

## `tensile_test/`
Single polyester filament pulled by hand over a rotary-motion pulley (force sensor, 20 Hz logging). Values are a down-sampled subset of the raw export used to drive the animation; force is raw (zero offset ≈ 0.015 N, subtracted in the overlay). Peak after correction ≈ 0.38 N at t = 13.35 s.
