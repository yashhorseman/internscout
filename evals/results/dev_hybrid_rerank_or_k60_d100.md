Setting: {'mode': 'hybrid_rerank', 'match': 'or', 'rrf_k': 60, 'depth': 100}
Queries scored: 26; with nothing relevant: 2; unlabeled results in top 10: 0

| Metric | Mean | 95% interval |
|---|---|---|
| recall@5 | 0.344 | 0.247 to 0.448 |
| recall@10 | 0.536 | 0.408 to 0.661 |
| mrr | 0.865 | 0.750 to 0.962 |
| ndcg@10 | 0.737 | 0.622 to 0.844 |

| Category | n | recall@5 | recall@10 | mrr | ndcg@10 |
|---|---|---|---|---|---|
| exact | 5 | 0.593 | 0.927 | 1.000 | 0.990 |
| location | 5 | 0.150 | 0.307 | 1.000 | 0.719 |
| remote | 2 | 0.875 | 1.000 | 1.000 | 0.990 |
| seniority | 5 | 0.359 | 0.579 | 0.800 | 0.705 |
| skill | 5 | 0.205 | 0.364 | 0.800 | 0.633 |
| vague | 4 | 0.163 | 0.265 | 0.625 | 0.488 |
