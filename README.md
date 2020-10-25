# Application dash

Cette application dash (codé en Python 3) permet d'afficher les différents bloxplots de chaque paramètre.
Les boxplots peuvent être filtrés par RegionHydro, puis par site/rivière.

Pour cela, il faut absolument avoir une matrice statistique (par exemple le fichier `matrice_statistique.csv`).
Pour que l'application fonctionne correctement, il faut que la matrice statistique soit de cette forme ci-dessous:

| IDPrelevement      |     Filtre_1    |   Filtre_2   |   Paramètre_1   |   Paramètre_2   |   ...    |   Paramètre_n |
| ------------------ |: -------------: | -----------: | --------------: | --------------: | -------: | ------------: |
| ...                |      ...        |    ...       |      ...        |      ...        |    ...   |     ...       |
| ...                |      ...        |    ...       |      ...        |      ...        |    ...   |     ...       |
| ...                |      ...        |    ...       |      ...        |      ...        |    ...   |     ...       |

Pour afficher les différents boxplots, le script ne prendra bien sûr pas en compte les champs vides, il est donc normal que chaque boxplot n'est pas généré par le même nombre d'observations.
Sur cette application, il est aussi possible d'activer (ou non) un filtre de Tukey. Le filtre de Tukey est un critère pour considérer si une valeur est considérée comme étant une valeur extrême.
Soit $X_i$ une valeur présente dans la matrice pour un paramètre $P$. $X_i$ est considérée comme étant une valeur extrême si elle n'est pas comprise dans l'intervalle $[Q_1 - 1.5 \times IQR; Q_3 + 1.5 \times IQR]$ 
avec $Q_1$ le premier quartile, $Q_3$ le troisième quartile et $IQR$ l'écart interquartile (ie. $Q_3 - Q_1$). 