Setting: {'mode': 'hybrid_rerank', 'match': 'or', 'rrf_k': 60, 'depth': 50}
Queries scored: 10; with nothing relevant: 2; unlabeled results in top 10: 0

| Metric | Mean | 95% interval |
|---|---|---|
| recall@5 | 0.482 | 0.287 to 0.672 |
| recall@10 | 0.619 | 0.454 to 0.767 |
| mrr | 0.917 | 0.750 to 1.000 |
| ndcg@10 | 0.719 | 0.545 to 0.859 |

| Category | n | recall@5 | recall@10 | mrr | ndcg@10 |
|---|---|---|---|---|---|
| exact | 2 | 1.000 | 1.000 | 1.000 | 1.000 |
| location | 2 | 0.258 | 0.667 | 1.000 | 0.655 |
| seniority | 2 | 0.583 | 0.583 | 1.000 | 0.712 |
| skill | 2 | 0.317 | 0.551 | 1.000 | 0.833 |
| vague | 2 | 0.250 | 0.295 | 0.583 | 0.398 |
