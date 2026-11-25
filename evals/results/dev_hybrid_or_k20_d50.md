Setting: {'mode': 'hybrid', 'match': 'or', 'rrf_k': 20, 'depth': 50}
Queries scored: 23; with nothing relevant: 5; unlabeled results in top 10: 0

| Metric | Mean | 95% interval |
|---|---|---|
| recall@5 | 0.469 | 0.357 to 0.591 |
| recall@10 | 0.688 | 0.580 to 0.799 |
| mrr | 0.949 | 0.870 to 1.000 |
| ndcg@10 | 0.807 | 0.710 to 0.881 |

| Category | n | recall@5 | recall@10 | mrr | ndcg@10 |
|---|---|---|---|---|---|
| exact | 5 | 0.706 | 0.971 | 1.000 | 0.960 |
| location | 5 | 0.214 | 0.408 | 1.000 | 0.808 |
| remote | 1 | 1.000 | 1.000 | 1.000 | 0.595 |
| seniority | 4 | 0.679 | 0.833 | 0.875 | 0.859 |
| skill | 5 | 0.310 | 0.529 | 0.867 | 0.682 |
| vague | 3 | 0.307 | 0.648 | 1.000 | 0.764 |
