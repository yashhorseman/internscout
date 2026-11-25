Setting: {'mode': 'hybrid_rerank', 'match': 'or', 'rrf_k': 60, 'depth': 100}
Queries scored: 23; with nothing relevant: 5; unlabeled results in top 10: 0

| Metric | Mean | 95% interval |
|---|---|---|
| recall@5 | 0.436 | 0.320 to 0.553 |
| recall@10 | 0.608 | 0.471 to 0.740 |
| mrr | 0.891 | 0.783 to 0.978 |
| ndcg@10 | 0.773 | 0.651 to 0.879 |

| Category | n | recall@5 | recall@10 | mrr | ndcg@10 |
|---|---|---|---|---|---|
| exact | 5 | 0.760 | 1.000 | 1.000 | 1.000 |
| location | 5 | 0.163 | 0.331 | 1.000 | 0.716 |
| remote | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| seniority | 4 | 0.617 | 0.833 | 0.875 | 0.862 |
| skill | 5 | 0.253 | 0.406 | 0.800 | 0.610 |
| vague | 3 | 0.226 | 0.319 | 0.667 | 0.569 |
