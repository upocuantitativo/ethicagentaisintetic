# Recursive analysis results

## Round 1: all entities, 4-class taxonomy  (n=89)
- Failed solvency claims: 0/4
  - [OK] C1_taxonomy_separable: RF 5-fold CV accuracy=0.73, bootstrap mean=0.68 (95% CI lower=0.52).
  - [OK] C2_kappa_above_0_70: Cohen's Kappa=0.772, bootstrap 95% CI lower=0.541.
  - [OK] C3_score_threshold_selects_synthetic_dominated: At score>=50 0.70 of selected entities fall in synthetic/DAO/shell classes.
  - [OK] C4_unsupervised_recovers_taxonomy_partially: At k=4, ARI(kmeans, agglom)=0.87, max ARI vs taxonomy=0.26.
- Cohen's Kappa (R1 vs R2, n=25): 0.772 (95% CI [0.541, 0.942])
- logistic: CV acc=0.639 +/- 0.082, F1m=0.407
- random_forest: CV acc=0.729 +/- 0.085, F1m=0.622
- gradient_boosting: CV acc=0.641 +/- 0.025, F1m=0.536

## Round 2: 2-class collapse (synthetic_or_dao vs agentic_or_other)  (n=89)
- Failed solvency claims: 1/4
  - [OK] C1_taxonomy_separable: RF 5-fold CV accuracy=0.92, bootstrap mean=0.90 (95% CI lower=0.78).
  - [OK] C2_kappa_above_0_70: Cohen's Kappa=0.772, bootstrap 95% CI lower=0.552.
  - [FAIL] C3_score_threshold_selects_synthetic_dominated: At score>=50 0.00 of selected entities fall in synthetic/DAO/shell classes.
  - [OK] C4_unsupervised_recovers_taxonomy_partially: At k=4, ARI(kmeans, agglom)=0.87, max ARI vs taxonomy=0.52.
- Cohen's Kappa (R1 vs R2, n=25): 0.772 (95% CI [0.552, 0.943])
- logistic: CV acc=0.922 +/- 0.027, F1m=0.920
- random_forest: CV acc=0.922 +/- 0.083, F1m=0.920
- gradient_boosting: CV acc=0.944 +/- 0.061, F1m=0.943

## Round 3: only score >= 40 entities (no easy controls)  (n=78)
- Failed solvency claims: 0/4
  - [OK] C1_taxonomy_separable: RF 5-fold CV accuracy=0.70, bootstrap mean=0.64 (95% CI lower=0.48).
  - [OK] C2_kappa_above_0_70: Cohen's Kappa=0.772, bootstrap 95% CI lower=0.537.
  - [OK] C3_score_threshold_selects_synthetic_dominated: At score>=50 0.70 of selected entities fall in synthetic/DAO/shell classes.
  - [OK] C4_unsupervised_recovers_taxonomy_partially: At k=5, ARI(kmeans, agglom)=0.94, max ARI vs taxonomy=0.29.
- Cohen's Kappa (R1 vs R2, n=25): 0.772 (95% CI [0.537, 0.943])
- logistic: CV acc=0.640 +/- 0.085, F1m=0.363
- random_forest: CV acc=0.704 +/- 0.150, F1m=0.568
- gradient_boosting: CV acc=0.678 +/- 0.160, F1m=0.547
