# Data Directory

This directory contains the datasets used for the **Student Digital Well‑Being Analytics** project.

- **raw/** – Original CSV files as provided (no modifications).
- **processed/** – Cleaned and feature‑engineered dataset ready for analysis (`processed_data.csv`).

## Schema (both train and test files)
| Column | Description |
|--------|-------------|
| Age | Age of the participant (years) |
| Gender | `Male` / `Female` |
| Academic_Level | Undergraduate / Graduate / High School |
| Country | Country of residence (e.g., Egypt) |
| Governorate | Sub‑region within the country |
| Avg_Daily_Usage_Hours | Average daily time spent on social media (hours) |
| Most_Used_Platform | Platform most frequently used (e.g., TikTok) |
| Affects_Academic_Performance | `Yes` / `No` – self‑reported impact |
| Sleep_Hours_Per_Night | Average sleep duration (hours) |
| Mental_Health_Score | Self‑rated mental health (1‑7, higher is better) |
| Relationship_Status | Relationship status (Single, In Relationship, etc.) |
| Conflicts_Over_Social_Media | Number of conflicts reported (0‑5) |
| Addicted_Score | Addiction score (1‑10) |

The **processed** file will contain additional engineered features such as `Sleep_Efficiency` and `Social_Media_Intensity`.
