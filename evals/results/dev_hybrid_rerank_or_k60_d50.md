Setting: {'mode': 'hybrid_rerank', 'match': 'or', 'rrf_k': 60, 'depth': 50}
Queries scored: 26; with nothing relevant: 2; unlabeled results in top 10: 0

| Metric | Mean | 95% interval |
|---|---|---|
| recall@5 | 0.351 | 0.257 to 0.454 |
| recall@10 | 0.570 | 0.459 to 0.682 |
| mrr | 0.870 | 0.759 to 0.966 |
| ndcg@10 | 0.764 | 0.656 to 0.864 |

| Category | n | recall@5 | recall@10 | mrr | ndcg@10 |
|---|---|---|---|---|---|
| exact | 5 | 0.593 | 0.927 | 1.000 | 0.990 |
| location | 5 | 0.179 | 0.360 | 1.000 | 0.762 |
| remote | 2 | 0.875 | 1.000 | 1.000 | 0.990 |
| seniority | 5 | 0.359 | 0.579 | 0.800 | 0.705 |
| skill | 5 | 0.205 | 0.391 | 0.800 | 0.665 |
| vague | 4 | 0.176 | 0.383 | 0.653 | 0.567 |
