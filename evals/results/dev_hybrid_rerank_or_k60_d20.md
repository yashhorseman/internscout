Setting: {'mode': 'hybrid_rerank', 'match': 'or', 'rrf_k': 60, 'depth': 20}
Queries scored: 26; with nothing relevant: 2; unlabeled results in top 10: 0

| Metric | Mean | 95% interval |
|---|---|---|
| recall@5 | 0.361 | 0.271 to 0.463 |
| recall@10 | 0.634 | 0.518 to 0.748 |
| mrr | 0.927 | 0.816 to 1.000 |
| ndcg@10 | 0.795 | 0.699 to 0.878 |

| Category | n | recall@5 | recall@10 | mrr | ndcg@10 |
|---|---|---|---|---|---|
| exact | 5 | 0.593 | 0.927 | 1.000 | 0.990 |
| location | 5 | 0.188 | 0.369 | 1.000 | 0.801 |
| remote | 2 | 0.875 | 1.000 | 1.000 | 0.990 |
| seniority | 5 | 0.359 | 0.868 | 0.822 | 0.807 |
| skill | 5 | 0.232 | 0.438 | 1.000 | 0.681 |
| vague | 4 | 0.193 | 0.369 | 0.750 | 0.574 |
