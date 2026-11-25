Setting: {'mode': 'hybrid_rerank', 'match': 'or', 'rrf_k': 60, 'depth': 20}
Queries scored: 23; with nothing relevant: 5; unlabeled results in top 10: 0

| Metric | Mean | 95% interval |
|---|---|---|
| recall@5 | 0.445 | 0.329 to 0.560 |
| recall@10 | 0.636 | 0.507 to 0.760 |
| mrr | 0.935 | 0.826 to 1.000 |
| ndcg@10 | 0.798 | 0.676 to 0.892 |

| Category | n | recall@5 | recall@10 | mrr | ndcg@10 |
|---|---|---|---|---|---|
| exact | 5 | 0.760 | 1.000 | 1.000 | 1.000 |
| location | 5 | 0.221 | 0.434 | 1.000 | 0.821 |
| remote | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| seniority | 4 | 0.617 | 0.833 | 0.875 | 0.863 |
| skill | 5 | 0.238 | 0.404 | 1.000 | 0.618 |
| vague | 3 | 0.226 | 0.367 | 0.667 | 0.569 |
