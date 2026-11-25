Setting: {'mode': 'hybrid', 'match': 'or', 'rrf_k': 100, 'depth': 50}
Queries scored: 23; with nothing relevant: 5; unlabeled results in top 10: 0

| Metric | Mean | 95% interval |
|---|---|---|
| recall@5 | 0.473 | 0.362 to 0.593 |
| recall@10 | 0.678 | 0.571 to 0.789 |
| mrr | 0.949 | 0.870 to 1.000 |
| ndcg@10 | 0.807 | 0.704 to 0.886 |

| Category | n | recall@5 | recall@10 | mrr | ndcg@10 |
|---|---|---|---|---|---|
| exact | 5 | 0.706 | 0.971 | 1.000 | 0.960 |
| location | 5 | 0.212 | 0.410 | 1.000 | 0.815 |
| remote | 1 | 1.000 | 1.000 | 1.000 | 0.595 |
| seniority | 4 | 0.704 | 0.858 | 0.875 | 0.879 |
| skill | 5 | 0.310 | 0.529 | 0.867 | 0.681 |
| vague | 3 | 0.307 | 0.533 | 1.000 | 0.721 |
