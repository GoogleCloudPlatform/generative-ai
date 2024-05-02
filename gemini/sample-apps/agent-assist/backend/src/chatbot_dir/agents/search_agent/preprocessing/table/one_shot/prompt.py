"""This is a python utility file."""

# pylint: disable=E0401

PROMPT_FOR_TABLE = """
Given a table, turn it into natural language. The table data needs to be retrieved for question answering. Therefore it is essential to not miss any single cell.
Think step-by-step. Look at all the row and column headers carefully.
Be as elaborative as possible.
It is critical to look at each and every data - cell, row and column before giving an answer.
Make sure you write about every table cell.
Make sure you do not miss any detail.

Example:

Table:
  0     1     2     3     4     5     6     7     8     9     10     11     12     13     14
0  Gross Premium  Gross Premium  Gross Premium  Gross Premium  Gross Premium  Gross Premium  Gross Premium  (Excluding GST)  (Excluding GST)  (Excluding GST)  (Excluding GST)  (Excluding GST)  (Excluding GST)  (Excluding GST)  (Excluding GST)
1 Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹)
2   Age\nBand   Age\nBand    50,000   1,00,000   1,50,000   2,00,000   2,50,000   2,50,000   2,50,000   3,00,000   3,50,000   4,00,000   4,00,000   4,50,000   5,00,000
3   Age\nBand   Age\nBand    50,000   1,00,000    None   2,00,000   2,50,000   2,50,000   2,50,000   3,00,000    None   4,00,000   4,00,000   4,50,000   5,00,000
4     0-17    0-17    2,494    2,785    3,011    3,209    3,422    3,422    3,422    3,575    3,652    3,729    3,729    3,806    4,004
5    18-35    18-35    3,219    3,594    3,886    4,141    4,416    4,416    4,416    4,613    4,712    4,812    4,812    4,912    5,166
6    36-45    36-45    3,825    4,271    4,617    4,921    5,248    5,248    5,248    5,481    5,599    5,718    5,718    5,836    6,139
7    46-50    46-50    4,996    5,579    6,032    6,428    6,855    6,855    6,855    7,161    7,315    7,469    7,469    7,624    8,020
8    51-55    51-55    7,772    8,679    9,383    10,000    10,664    10,664    10,664    11,139    11,378    11,619    11,619    11,860    12,475
9    56-60    56-60    8,882    9,919    10,723    11,428    12,187    12,187    12,187    12,730    13,004    13,279    13,279    13,554    14,257
10    61-65    61-65    12,213    13,638    14,744    15,714    16,758    16,758    16,758    17,503    17,880    18,258    18,258    18,637    19,604
11    66-70    66-70    15,544    17,358    18,765    20,000    21,328    21,328    21,328    22,277    22,757    23,238    23,238    23,720    24,951
12    71-75    71-75    19,985    22,317    24,127    25,714    27,422    27,422    27,422    28,642    29,259    29,877    29,877    30,497    32,079
13    76-80    76-80    19,985    22,317    24,127    25,714    27,422    27,422    27,422    28,642    29,259    29,877    29,877    30,497    32,079
14     >80     >80    19,985    22,317    24,127    25,714    27,422    27,422    27,422    28,642    29,259    29,877    29,877    30,497    32,079
15 Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹) Sum Insured (in ₹)
16   Age\nBand    None    None   6,00,000    None   7,00,000   7,50,000   7,50,000   8,00,000   8,00,000    None   9,00,000   9,50,000   9,50,000   10,00,000
17   Age\nBand    None    None   6,00,000    None   7,00,000   7,50,000   7,50,000   8,00,000   8,00,000    None   9,00,000   9,50,000   9,50,000   10,00,000
18    0-17    4,165    4,165    4,309    4,440    4,555    4,668    4,668    4,781    4,781    4,894    5,002    5,108    5,108    5,207
19    18-35    5,375    5,375    5,560    5,729    5,878    6,024    6,024    6,170    6,170    6,315    6,454    6,591    6,591    6,719
20    36-45    6,387    6,387    6,607    6,808    6,984    7,158    7,158    7,331    7,331    7,505    7,670    7,832    7,832    7,984
21    46-50    8,343    8,343    8,631    8,894    9,124    9,350    9,350    9,577    9,577    9,804    10,019    10,232    10,232    10,429
22    51-55    12,979    12,979    13,426    13,835    14,193    14,545    14,545    14,898    14,898    15,250    15,586    15,916    15,916    16,223
23    56-60    14,833    14,833    15,344    15,811    16,220    16,623    16,623    17,026    17,026    17,429    17,812    18,189    18,189    18,541
24    61-65    20,395    20,395    21,098    21,740    22,303    22,857    22,857    23,411    23,411    23,964    24,492    25,010    25,010    25,494
25    66-70    25,958    25,958    26,853    27,669    28,385    29,090    29,090    29,795    29,795    30,500    31,171    31,832    31,832    32,447
26    71-75    33,374    33,374    34,525    35,575    36,496    37,402    37,402    38,308    38,308    39,214    40,078    40,926    40,926    41,717
27    76-80    33,374    33,374    34,525    35,575    36,496    37,402    37,402    38,308    38,308    39,214    40,078    40,926    40,926    41,717
28     >80    33,374    33,374    34,525    35,575    36,496    37,402    37,402    38,308    38,308    39,214    40,078    40,926    40,926    41,717

Output:
The table shows the gross premium (excluding GST) for different sum insured amounts and age bands.

For a sum insured of ₹50,000, the gross premium ranges from ₹2,494 to ₹4,165, depending on the age band.
- For the 0-17 age band, the gross premium is ₹2,494.
- For the 18-35 age band, the gross premium is ₹3,219.
- For the 36-45 age band, the gross premium is ₹3,825.
- For the 46-50 age band, the gross premium is ₹4,996.
- For the 51-55 age band, the gross premium is ₹7,772.
- For the 56-60 age band, the gross premium is ₹8,882.
- For the 61-65 age band, the gross premium is ₹12,213.
- For the 66-70 age band, the gross premium is ₹15,544.
- For the 71-75 age band, the gross premium is ₹19,985.
- For the 76-80 age band, the gross premium is ₹19,985.
- For the >80 age band, the gross premium is ₹19,985.

For a sum insured of ₹1,00,000, the gross premium ranges from ₹2,785 to ₹5,375, depending on the age band.
- For the 0-17 age band, the gross premium is ₹2,785.
- For the 18-35 age band, the gross premium is ₹3,594.
- For the 36-45 age band, the gross premium is ₹4,271.
- For the 46-50 age band, the gross premium is ₹5,579.
- For the 51-55 age band, the gross premium is ₹8,679.
- For the 56-60 age band, the gross premium is ₹9,919.
- For the 61-65 age band, the gross premium is ₹13,638.
- For the 66-70 age band, the gross premium is ₹17,358.
- For the 71-75 age band, the gross premium is ₹22,317.
- For the 76-80 age band, the gross premium is ₹22,317.
- For the >80 age band, the gross premium is ₹22,317.

For a sum insured of ₹1,50,000, the gross premium ranges from ₹3,011 to ₹6,607, depending on the age band.
- For the 0-17 age band, the gross premium is ₹3,011.
- For the 18-35 age band, the gross premium is ₹3,886.
- For the 36-45 age band, the gross premium is ₹4,617.
- For the 46-50 age band, the gross premium is ₹6,032.
- For the 51-55 age band, the gross premium is ₹9,383.
- For the 56-60 age band, the gross premium is ₹10,723.
- For the 61-65 age band, the gross premium is ₹14,744.
- For the 66-70 age band, the gross premium is ₹18,765.
- For the 71-75 age band, the gross premium is ₹24,127.
- For the 76-80 age band, the gross premium is ₹24,127.
- For the >80 age band, the gross premium is ₹24,127.

For a sum insured of ₹2,00,000, the gross premium ranges from ₹3,209 to ₹6,808, depending on the age band.
- For the 0-17 age band, the gross premium is ₹3,209.
- For the 18-35 age band, the gross premium is ₹4,141.
- For the 36-45 age band, the gross premium is ₹4,921.
- For the 46-50 age band, the gross premium is ₹6,428.
- For the 51-55 age band, the gross premium is ₹10,000.
- For the 56-60 age band, the gross premium is ₹11,428.
- For the 61-65 age band, the gross premium is ₹15,714.
- For the 66-70 age band, the gross premium is ₹20,000.
- For the 71-75 age band, the gross premium is ₹25,714.
- For the 76-80 age band, the gross premium is ₹25,714.
- For the >80 age band, the gross premium is ₹25,714.

For a sum insured of ₹2,50,000, the gross premium ranges from ₹3,422 to ₹7,158, depending on the age band.
- For the 0-17 age band, the gross premium is ₹3,422.
- For the 18-35 age band, the gross premium is ₹4,416.
- For the 36-45 age band, the gross premium is ₹5,248.
- For the 46-50 age band, the gross premium is ₹6,855.
- For the 51-55 age band, the gross premium is ₹10,664.
- For the 56-60 age band, the gross premium is ₹12,187.
- For the 61-65 age band, the gross premium is ₹16,758.
- For the 66-70 age band, the gross premium is ₹21,328.
- For the 71-75 age band, the gross premium is ₹27,422.
- For the 76-80 age band, the gross premium is ₹27,422.
- For the >80 age band, the gross premium is ₹27,422.

For a sum insured of ₹3,00,000, the gross premium ranges from ₹3,575 to ₹7,331, depending on the age band.
- For the 0-17 age band, the gross premium is ₹3,575.
- For the 18-35 age band, the gross premium is ₹4,613.
- For the 36-45 age band, the gross premium is ₹5,481.
- For the 46-50 age band, the gross premium is ₹7,161.
- For the 51-55 age band, the gross premium is ₹11,139.
- For the 56-60 age band, the gross premium is ₹12,730.
- For the 61-65 age band, the gross premium is ₹17,880.
- For the 66-70 age band, the gross premium is ₹22,757.
- For the 71-75 age band, the gross premium is ₹28,642.
- For the 76-80 age band, the gross premium is ₹28,642.
- For the >80 age band, the gross premium is ₹28,642.

For a sum insured of ₹3,50,000, the gross premium ranges from ₹3,652 to ₹7,505, depending on the age band.
- For the 0-17 age band, the gross premium is ₹3,652.
- For the 18-35 age band, the gross premium is ₹4,712.
- For the 36-45 age band, the gross premium is ₹5,599.
- For the 46-50 age band, the gross premium is ₹7,315.
- For the 51-55 age band, the gross premium is ₹11,378.
- For the 56-60 age band, the gross premium is ₹13,004.
- For the 61-65 age band, the gross premium is ₹18,258.
- For the 66-70 age band, the gross premium is ₹23,238.
- For the 71-75 age band, the gross premium is ₹29,259.
- For the 76-80 age band, the gross premium is ₹29,259.
- For the >80 age band, the gross premium is ₹29,259.

For a sum insured of ₹4,00,000, the gross premium ranges from ₹3,729 to ₹7,670, depending on the age band.
- For the 0-17 age band, the gross premium is ₹3,729.
- For the 18-35 age band, the gross premium is ₹4,812.
- For the 36-45 age band, the gross premium is ₹5,718.
- For the 46-50 age band, the gross premium is ₹7,469.
- For the 51-55 age band, the gross premium is ₹11,619.
- For the 56-60 age band, the gross premium is ₹13,279.
- For the 61-65 age band, the gross premium is ₹18,637.
- For the 66-70 age band, the gross premium is ₹23,720.
- For the 71-75 age band, the gross premium is ₹29,877.
- For the 76-80 age band, the gross premium is ₹29,877.
- For the >80 age band, the gross premium is ₹29,877.

For a sum insured of ₹4,50,000, the gross premium ranges from ₹3,806 to ₹7,832, depending on the age band.
- For the 0-17 age band, the gross premium is ₹3,806.
- For the 18-35 age band, the gross premium is ₹4,912.
- For the 36-45 age band, the gross premium is ₹5,836.
- For the 46-50 age band, the gross premium is ₹7,624.
- For the 51-55 age band, the gross premium is ₹11,860.
- For the 56-60 age band, the gross premium is ₹13,554.
- For the 61-65 age band, the gross premium is ₹19,604.
- For the 66-70 age band, the gross premium is ₹24,951.
- For the 71-75 age band, the gross premium is ₹30,497.
- For the 76-80 age band, the gross premium is ₹30,497.
- For the >80 age band, the gross premium is ₹30,497.

For a sum insured of ₹5,00,000, the gross premium ranges from ₹4,004 to ₹7,984, depending on the age band.
- For the 0-17 age band, the gross premium is ₹4,004.
- For the 18-35 age band, the gross premium is ₹5,166.
- For the 36-45 age band, the gross premium is ₹6,139.
- For the 46-50 age band, the gross premium is ₹8,020.
- For the 51-55 age band, the gross premium is ₹12,475.
- For the 56-60 age band, the gross premium is ₹14,257.
- For the 61-65 age band, the gross premium is ₹20,395.
- For the 66-70 age band, the gross premium is ₹25,958.
- For the 71-75 age band, the gross premium is ₹32,079.
- For the 76-80 age band, the gross premium is ₹32,079.
- For the >80 age band, the gross premium is ₹32,079.

Table: {}

Output:

"""
