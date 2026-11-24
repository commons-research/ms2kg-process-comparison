# Wikidata taxon–chemical candidate pairs

Each pair links the identified source taxon of a biological sample to a candidate’s native Wikidata reference through that sample’s acquisition and raw file. A shared pair means both pipelines reported the same two Wikidata items in that trial. It does not establish compound presence, feature alignment or independent experimental confirmation.

| Trial | ENPKG | Flock | Both | ENPKG only | Flock only | Union |
|---|---:|---:|---:|---:|---:|---:|
| first | 936 | 4857 | 212 | 724 | 4645 | 5581 |
| second | 934 | 4857 | 211 | 723 | 4646 | 5580 |

## Pairs by annotation software and procedure

For each row, “Also in other” counts distinct pairs found anywhere in the other pipeline in the same trial. “Exclusive” counts pairs absent from that pipeline. Software totals take the union across procedures. A reported method with no qualifying pair has a count of zero.

| Trial | Pipeline | Software | Procedure | Pairs | Also in other | Exclusive | Full key | Connectivity only | Unverified |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| first | enpkg | [Q124358188](<http://www.wikidata.org/entity/Q124358188>) | All procedures | 494 | 41 | 453 | 0 | 494 | 0 |
| first | enpkg | [Q124358188](<http://www.wikidata.org/entity/Q124358188>) | [CSIFingerID](<https://v6.docs.sirius-ms.io/methods-background/#CSIFingerID>) | 494 | 41 | 453 | 0 | 494 | 0 |
| first | enpkg | [enpkg_full](<https://github.com/enpkg/enpkg_full>) | All procedures | 482 | 181 | 301 | 0 | 482 | 0 |
| first | enpkg | [enpkg_full](<https://github.com/enpkg/enpkg_full>) | [03_enpkg_mn_isdb_isdb_taxo](<https://github.com/enpkg/enpkg_full/blob/a6535a5dfda9f4c59c79f39401359cb14c521a86/03_enpkg_mn_isdb_isdb_taxo/README.md>) | 482 | 181 | 301 | 0 | 482 | 0 |
| first | flock | [hocofaisan](<https://github.com/oolonek/hocofaisan>) | All procedures | 4857 | 212 | 4645 | 2596 | 2261 | 0 |
| first | flock | [hocofaisan](<https://github.com/oolonek/hocofaisan>) | [reference-preparation-and-annotation](<https://github.com/oolonek/hocofaisan/blob/1d779f55165b1b227e16ebe126ec2675c47203c8/TECHNICAL.md#reference-preparation-and-annotation>) | 4857 | 212 | 4645 | 2596 | 2261 | 0 |
| second | enpkg | [Q124358188](<http://www.wikidata.org/entity/Q124358188>) | All procedures | 493 | 41 | 452 | 0 | 493 | 0 |
| second | enpkg | [Q124358188](<http://www.wikidata.org/entity/Q124358188>) | [CSIFingerID](<https://v6.docs.sirius-ms.io/methods-background/#CSIFingerID>) | 493 | 41 | 452 | 0 | 493 | 0 |
| second | enpkg | [enpkg_full](<https://github.com/enpkg/enpkg_full>) | All procedures | 481 | 180 | 301 | 0 | 481 | 0 |
| second | enpkg | [enpkg_full](<https://github.com/enpkg/enpkg_full>) | [03_enpkg_mn_isdb_isdb_taxo](<https://github.com/enpkg/enpkg_full/blob/a6535a5dfda9f4c59c79f39401359cb14c521a86/03_enpkg_mn_isdb_isdb_taxo/README.md>) | 481 | 180 | 301 | 0 | 481 | 0 |
| second | flock | [hocofaisan](<https://github.com/oolonek/hocofaisan>) | All procedures | 4857 | 211 | 4646 | 2596 | 2261 | 0 |
| second | flock | [hocofaisan](<https://github.com/oolonek/hocofaisan>) | [reference-preparation-and-annotation](<https://github.com/oolonek/hocofaisan/blob/1d779f55165b1b227e16ebe126ec2675c47203c8/TECHNICAL.md#reference-preparation-and-annotation>) | 4857 | 211 | 4646 | 2596 | 2261 | 0 |

The last three columns count distinct pairs with each kind of candidate-to-reference evidence. Full key requires identical complete InChIKeys. Connectivity only requires matching first blocks without a complete-key match. Unverified retains native associations with missing or disagreeing keys. One pair may have evidence in several columns or from several methods. See [pair-evidence.tsv](pair-evidence.tsv) for each distinct combination.
