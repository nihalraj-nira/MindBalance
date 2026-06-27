# Add Behavioural Similarity Search (KNN)

Your teammate proved that macro-clustering only yields 2 broad groups. To provide highly personalised insights, we will implement micro-clustering using **K-Nearest Neighbors (KNN)**.

## Open Questions
None. The logic is mathematically straightforward and relies on `scikit-learn` which we already have installed.

## Proposed Changes

### 1. `06_whatif_api.py`
We will update the backend API to include a similarity search engine.

- **[MODIFY] `06_whatif_api.py`**
  - **Startup**: Train a `sklearn.neighbors.NearestNeighbors` model on the scaled training dataset (`X_train.csv`) when the server starts.
  - **New Function**: Create `find_similar_students(processed_row, k=5)` which returns the data of the 5 closest students.
  - **Endpoint Update**: Modify the `/predict` endpoint so the JSON response includes a new `similar_students` block.

## Verification Plan
1. Restart the Flask API.
2. Send a POST request to `/predict`.
3. Verify that the response includes a list of 5 similar students, their features, and their respective addiction scores.
