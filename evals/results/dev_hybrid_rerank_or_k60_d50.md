Setting: {'mode': 'hybrid_rerank', 'match': 'or', 'rrf_k': 60, 'depth': 50}
Queries scored: 23; with nothing relevant: 5; unlabeled results in top 10: 0

| Metric | Mean | 95% interval |
|---|---|---|
| recall@5 | 0.440 | 0.325 to 0.556 |
| recall@10 | 0.636 | 0.509 to 0.760 |
| mrr | 0.891 | 0.783 to 0.978 |
| ndcg@10 | 0.789 | 0.668 to 0.886 |

| Category | n | recall@5 | recall@10 | mrr | ndcg@10 |
|---|---|---|---|---|---|
| exact | 5 | 0.760 | 1.000 | 1.000 | 1.000 |
| location | 5 | 0.182 | 0.380 | 1.000 | 0.753 |
| remote | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| seniority | 4 | 0.617 | 0.833 | 0.875 | 0.862 |
| skill | 5 | 0.253 | 0.459 | 0.800 | 0.646 |
| vague | 3 | 0.226 | 0.367 | 0.667 | 0.569 |
