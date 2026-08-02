# Dataset Preparation & Preprocessing Protocol

**Version**: v1.5.0-ml-validation  
**Date**: August 3, 2026  

---

## 1. Feature Engineering & Preprocessing

* **Missing Blood Pressure Imputation**: Missing BP values are defaulted to $120.0$ / $80.0$ mmHg for normalization while retaining explicit `bp_source = "none"` in DB records.
* **StandardScaler Normalization**: Features are scaled using Z-score transformation before tensor construction:
  $$\hat{x} = \frac{x - \mu}{\sigma}$$
* **Sliding Window Construction**: Creates overlapping 60-sample matrices.

---

## 2. Proxy Label Derivation

To avoid diagnostic misrepresentation, proxy risk labels were derived from deterministic clinical guidelines:
* `normal` (0): $95\% \le SpO_2 \le 100\%$, $60 \le HR \le 100$
* `warning` (1): $92\% \le SpO_2 < 95\%$, or $100 < HR \le 120$
* `critical` (2): $SpO_2 < 92\%$, or $HR > 150$ or $HR < 40$
