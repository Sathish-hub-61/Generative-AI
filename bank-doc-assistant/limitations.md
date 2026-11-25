# Limitations Report

### 1. 1 of 11 columns have no documentation
- **Severity:** HIGH
- **Rule:** R001
- **Evidence:** Undocumented columns: conversion_status (col #11)

### 2. Placeholder-like values in 'occupation'
- **Severity:** LOW
- **Rule:** R003
- **Evidence:** Column 'occupation' (col #1): 288 occurrences observed ('unidentified': 288) at rows [33, 651, 773, 816, 1062, 1260, 1358, 1588, 1676, 1820, 1921, 1972 ... (+276 more)]

### 3. Placeholder-like values in 'education_level'
- **Severity:** LOW
- **Rule:** R003
- **Evidence:** Column 'education_level' (col #3): 1857 occurrences observed ('unidentified': 1857) at rows [2, 33, 101, 102, 116, 123, 184, 194, 255, 290, 303, 322 ... (+1845 more)]

### 4. Placeholder-like values in 'communication_channel'
- **Severity:** LOW
- **Rule:** R003
- **Evidence:** Column 'communication_channel' (col #5): 13020 occurrences observed ('unidentified': 13020) at rows [1, 2, 6, 11, 15, 20, 24, 25, 29, 33, 36, 38 ... (+13008 more)]

### 5. Placeholder-like values in 'call_duration'
- **Severity:** LOW
- **Rule:** R003
- **Evidence:** Column 'call_duration' (col #8): 4 occurrences observed ('0': 3, '999': 1) at rows [835, 14778, 36814, 43257]

### 6. Placeholder-like values in 'previous_campaign_outcome'
- **Severity:** LOW
- **Rule:** R003
- **Evidence:** Column 'previous_campaign_outcome' (col #10): 36959 occurrences observed ('unidentified': 36959) at rows [2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15 ... (+36947 more)]

### 7. IQR outliers in 'age'
- **Severity:** MEDIUM
- **Rule:** R006
- **Evidence:** Column 'age' (col #2): 487 outlier values outside [10.50, 70.50] at rows [18, 293, 304, 479, 625, 810, 813, 816, 848, 906, 941, 951 ... (+475 more)] (sample values: 71, 77, 73, 74, 75)

### 8. IQR outliers in 'call_duration'
- **Severity:** MEDIUM
- **Rule:** R006
- **Evidence:** Column 'call_duration' (col #8): 3235 outlier values outside [-221.00, 643.00] at rows [8, 11, 13, 21, 94, 115, 156, 166, 174, 188, 191, 196 ... (+3223 more)] (sample values: 651, 647, 961, 1834, 891)

### 9. IQR outliers in 'call_frequency'
- **Severity:** MEDIUM
- **Rule:** R006
- **Evidence:** Column 'call_frequency' (col #9): 3064 outlier values outside [-2.00, 6.00] at rows [11, 36, 41, 42, 45, 46, 65, 69, 77, 89, 131, 168 ... (+3052 more)] (sample values: 7, 17, 13, 7, 19)

### 10. Duplicate rows detected
- **Severity:** MEDIUM
- **Rule:** R007
- **Evidence:** 6 exact duplicate rows found across all 11 columns at rows [24558, 28502, 34864, 35525, 38396, 41489]
